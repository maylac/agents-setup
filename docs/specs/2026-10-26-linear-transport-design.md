# Linear transport(GitHub 併用)設計書

日付: 2026-10-26
状態: 設計案(未実装)。この文書を作るところまでは承認済みです。PR の merge、Linear への書き込み、API キーの発行、launchd の変更、bridge の再起動は、それぞれ別に本人の承認が要ります。
依頼元: Gota 本人(Grok Bot 経由。2026-10-25 19:04 JST に依頼、19:06 JST に第1工程の範囲を承認)
対象コード: `slack-bridge/bridge.py`(この文書の行番号は `git show f688563:slack-bridge/bridge.py` の行番号)、`slack-bridge/harness.py`

## 0. 前提と結論

- 正本は GitHub のまま変えません(`BRIDGE_TRANSPORT=github` の経路と `maylac/agent-tasks` はそのまま残す)。Linear は 2 つ目の受け口として足すだけです。
- 推奨案: **既存プロセスには触らず、`BRIDGE_TRANSPORT=linear` で動く 2 つ目の launchd ジョブを足す。両プロセスは `run.lock` を共有し、agent の実行は 1 本ずつに保つ。**(詳しくは 1 章)
- 処理済みの印: **`agent-task` ラベルを外すこと**の一つに決めます。GitHub と同じく、実行前に外します(3 章)。
- 契約のヘッダー 4 行は Linear に保存されても変わりませんでした。現行の `parse_contract` も、取り直した本文をそのまま読めました(付録 A)。

### 改訂履歴

- 2026-11-01: Codex の読み取り検品(maylac/agent-tasks#10、判定「要修正」)の指摘 4 件に対応しました。どの指摘への対応かは本文中に「検品#10 指摘N」と書いてあります。
  - 指摘1(Linear の鍵が子 agent に渡る): 5 章「子プロセスへの鍵の継承を防ぐ」、7 章テスト 13・14
  - 指摘2(creator の許可リストだけでは編集者を制限できない): 4 章「信頼境界と起票後の改変検出」、7 章テスト 15〜18
  - 指摘3(状態遷移の途中でクラッシュするとタスクが監視から消える): 6 章「状態遷移ごとの失敗と回復」、7 章テスト 19〜26、8 章 51 行目
  - 指摘4(Linear API の実仕様が未検証): 10 章「実装前の API 検証と smoke 受け入れ条件」、7 章「段階的な導入」の 2a

## 1. bridge.py に linear 経路を足す方式(併用)

### 現行の構造(HEAD f688563)

| 行 | 内容 |
|---|---|
| 45–48 | `load_config`: `transport = env.get("BRIDGE_TRANSPORT", "slack")`。値は `slack` か `github` のどちらか一つ |
| 50 | 必須キーは transport ごとに切り替わる(github なら `BRIDGE_GITHUB_REPO`) |
| 63 | `"state"`: `~/.local/state/slack-bridge/last_ts`(Slack 経路の `poll_once` だけが使う) |
| 64 | `"worktrees"`: `~/.local/state/slack-bridge/worktrees` |
| 77 | `"cooldowns"`: `~/.local/state/slack-bridge/cooldowns.json` |
| 210–217 | `run_task`: `name = "bridge-" + task_id` の名前で `git worktree add -b` |
| 218 | `cool = harness.Cooldowns(cfg["cooldowns"])` |
| 292–293 | `gh()`: `subprocess.run(["gh"] + ..., check=True)`。失敗すると例外を投げる |
| 296–297 | `github_tasks`: `author.login` が `cfg["senders"]` に入っているか見る |
| 300–314 | `poll_github_once`: 一覧取得 → ラベル削除(307) → `run_task`(309、task_id は `"gh%s-%d"`) → `needs-approval` ならラベルを付けて開いたまま残す(310–312)、それ以外は close(314) |
| 317–325 | `main`: transport に応じて poll 関数を 1 つ選び(319)、例外は stderr に出して続行する(323–324) |

`harness.Cooldowns.mark`(harness.py 111–118)は、ファイルを読み、書き換え、`os.replace` で戻します。原子的に置き換わるのは書き込みの瞬間だけで、読みから書きまでの間にロックはありません。

### 比較

| 観点 | 案 A: 単一 transport のまま 2 つ目のプロセスを足す | 案 B: 1 プロセスで複数 transport を回す(`BRIDGE_TRANSPORTS=github,linear`) |
|---|---|---|
| 導入時の既存 bridge 再起動 | **不要**(新しい launchd ジョブを足すだけ) | **必要**(動いている `com.maylac.slack-bridge` を入れ替える。Hard Stop) |
| 戻し方 | Linear 側のジョブを止めれば終わり。GitHub 側は一度も止めない | env を戻し、もう一度再起動する(また Hard Stop) |
| 障害の切り分け | Linear API の不調が GitHub 側のループに届かない | 同じループの中。poll ごとに try で包む必要がある |
| 同時実行 | 2 つの agent が並んで走りうる → `run.lock` で 1 本ずつにする | もともと 1 本ずつ |
| state file(63 行) | 衝突しない。`last_ts` は Slack 経路だけが使い、github/linear は読まない | 衝突しない |
| worktrees(64 行) | ディレクトリは共有する。名前は `bridge-gh…` と `bridge-lin…` で分かれるので重ならない。ただし同じ repo に `git worktree add` が同時に走ると、git のロック競合で失敗しうる → `run.lock` で防ぐ | 1 本ずつなので衝突しない |
| cooldowns(77 行) | **共有するのが正しい**(route の不調は transport に関係しない)。ただし `mark` の読みと書きの間で更新が消えうる → `run.lock` の中でしか呼ばれないので、ロックがあれば消えない | 衝突しない |
| コード量 | `load_config` に分岐を 1 つ、`poll_linear_once` を 1 つ、ロックを 1 つ | 上に加えて、config を transport ごとに分ける作業 |

### 推奨: 案 A

- 理由 1: 導入と戻しのどちらでも、動いている GitHub bridge(実行中の agent ごと)を止めずに済みます。再起動の承認が要る回数が一番少ない案です。
- 理由 2: 衝突しうるのは worktree の作成と cooldowns の同時書き込みだけで、どちらも `run_task` の中で起きます。共有ロック 1 つで両方を防げます。
- 注意点: 動いている GitHub プロセスは古いコードを読み込んだままなので、次に再起動されるまで `run.lock` を取りません。それまでは同時実行がありえます。試験期間(bridge-test project で 1 件ずつ)なら許容範囲とし、GitHub 側は本人の承認を得てから、空いている時間に再起動してロックを有効にします(7 章)。

### 変更箇所(実装するときの具体案)

1. `load_config`(46–50 行): 47 行目の許可値に `"linear"` を足します。linear の必須キーは `LINEAR_API_KEY`, `BRIDGE_LINEAR_TEAM`, `BRIDGE_LINEAR_PROJECT`, `BRIDGE_LINEAR_ALLOWED_CREATORS` です。戻り値に `linear_*` のキーと `"run_lock"`(既定は `~/.local/state/slack-bridge/run.lock`)を足します。
2. `run_task`(162 行〜): 210–217 行の worktree 作成から 253 行のループの終わりまでを、`fcntl.flock(LOCK_EX)` を取った `run.lock` の中で実行します。ロックを持つ間は待つだけにして、ロックを諦める処理は作りません。
3. 新しい関数 `linear(cfg, query, variables)`: GraphQL への入口はこの 1 か所だけにします(`gh()` と同じ役割で、テストではここを差し替える)。
4. 新しい関数 `linear_tasks(issues, cfg)`: `github_tasks`(296 行)の Linear 版です。
5. 新しい関数 `poll_linear_once(cfg)`: `poll_github_once`(300–314 行)と同じ流れにします。task_id は `"lin%s-%d" % (identifier, time)`(例: `linCA1-5-1792...`。git の branch 名に使える文字だけになる)。
6. `main`(319 行): `{"github": poll_github_once, "linear": poll_linear_once}.get(transport, poll_once)` の形にします。
7. launchd: `launchd/com.maylac.linear-bridge.plist.template` を新しく作ります(Label と env ファイル名だけを変える。ログは `linear-out.log` / `linear-err.log`)。

## 2. 契約フォーマットの Linear 対応

### 試験から分かったこと(付録 A で SHA256 を再計算済み)

Linear は保存するときに説明欄を Markdown として正規化します。変わった点は次のとおりです。`1)` が `1.` になりその前に空行が入る、`-` が `*` になる、行末スペースが消える、`#` と `>` の前に空行が入る、` ```fence``` ` が `` `fence` `` になる、`\n` が `\\n` になる、末尾の改行が消える。
変わらなかったのは、ヘッダー 4 行、その後の空行、`Goal:`、`Owned files:`、単一バッククォートの中の連続スペース、山括弧、HTML コメント、`&`、引用符、日本語、絵文字、全角文字です。

### ヘッダーのパース規則

現行の `parse_contract`(81–96 行)は `text.strip().partition("\n\n")`(83 行)で最初の空行を探し、そこまでをヘッダーとして読みます。取り直した本文でもこのまま 4 キーを読めることを確認しました(付録 A)。そのうえで、次の正規化を `parse_contract` の頭に 1 か所だけ足します。GitHub 経路にも同じ処理が掛かりますが、受け付ける入力が増えるだけなので後方互換です。

1. `\r\n` と `\r` を `\n` にそろえる。
2. 空白だけの行を空行として扱う(`partition("\n\n")` は `"\n \n"` を区切りと見なせないため)。
3. 先頭の空行と末尾の改行の有無は無視する(`strip()` のままでよい)。
4. ヘッダーは、先頭から最初の空行までの `key: value` 行とする。ヘッダーと本文の間に空行がいくつあっても 1 つとして扱う。
5. ヘッダーの値に `\`、`*`、`[`、`` ` `` が入っていたら、`rejected: header value looks markdown-escaped` として拒否する。Linear が値をエスケープしたりリンクにしたりした場合に、壊れた値で実行しないためです。`repo:` は 172–175 行の realpath 許可リストでも守られていますが、拒否理由が分かるようにここでも止めます。
6. キーの許可(`agent`/`repo`/`model`/`fallback`)と必須の検証(92–95 行)は今のままです。

### 本文の書き方(Dispatcher への規則)

- 番号付きの項目は `1)` や `- ` ではなく `A1:` `A2:` のように書く(リストに変換されない平文)。
- コマンドは単一バッククォートで書く(試験で保たれた)。トリプルバッククォートは使わない。
- バックスラッシュは書かない(エスケープが二重になる)。改行コードやパスの区切りは言葉で書くか、ファイルに置く。
- 行末スペースでの改行、空行の数、箇条書きの記号に意味を持たせない。
- 起票は 2 段階にする。ラベルなしで作る → `get_issue` で取り直し、ヘッダー 4 行が送ったものと一致するか確かめる → 一致したら `agent-task` を付ける。正規化で壊れた契約は、こうすれば実行されません。

## 3. 状態の対応表

| GitHub(現行) | Linear(提案) |
|---|---|
| open Issue + `agent-task` ラベル | team Ca1yam、対象 project、`agent-task` ラベル付き、状態の type が `completed`/`canceled` 以外(Dispatcher は Todo で作る。Backlog でも拾う) |
| ラベル削除(307 行。実行前) | **`agent-task` ラベルを外す = 処理済みの印**。外した後に issue を取り直し、ラベルが本当に消えたかを確かめてから実行する。続けて状態を In Progress にする |
| `gh issue comment`(308 行) | `commentCreate`。最初の `say`(`started: …`)を親コメントにし、以後の `say` は `parentId` にその ID を入れた返信にする。本文の先頭には必ず `[bridge]` を付ける |
| close(314 行) | `done` → Done。`rejected`/`failed …`/`blocked …` → Canceled。判断の材料はコメント 1 行目の status で、状態は見やすさのためだけ |
| `needs-approval` ラベル + open のまま(310–312 行) | `needs-approval` ラベルを付けて In Progress のまま残す |
| (なし) | Duplicate は bridge では使わない |

状態は名前ではなく ID で更新します。起動時に team の workflowStates から `BRIDGE_LINEAR_STATE_STARTED/DONE/CANCELED`(既定は `In Progress`/`Done`/`Canceled`)の ID を探し、見つからなければ起動しません(fail closed)。

処理済みの印を状態ではなくラベルにする理由は 3 つです。(1) GitHub と同じ規則になる。(2) 新しい issue は Backlog で作られるので、状態を合図にすると UI で状態を動かしただけで誤って実行されうる。(3) ラベルは Dispatcher が付けたときだけ実行される、はっきりした合図になる。

## 4. 起票者の許可

- 判定: `issue.creator.id` が `BRIDGE_LINEAR_ALLOWED_CREATORS`(Linear のユーザー UUID をカンマ区切り)に入っているかで判定します。これに加えて、team と project が一致し、`agent-task` ラベルが付いている必要があります。表示名やメールアドレスでは判定しません。
- 前提: Grok Bot のコネクタは Gota 本人の OAuth で動くので、Dispatcher が作った issue の creator は Gota 本人です(報告にあった ID は `34c874b1-7e9e-492f-afda-9375e8f845a8`。コード屋は未確認)。そのため、**Gota 本人が手で作った issue と区別できません**。
- 誤起票のリスクと対策:
  - 本人が手で `agent-task` を付けると実行される → ラベルは Dispatcher だけが付けるという運用規則にする。対象を専用 project に絞り、普段使う project とは混ぜない。
  - 起票後に説明欄が書き換えられる、別の人がラベルを付ける → 下の「信頼境界と起票後の改変検出」で fail closed にする(警告だけでは済ませない)。
  - 連携機能(メールからの起票、フォーム、Slack 連携など)で作られた issue → creator は連携側のユーザーになるので許可リストで弾かれる(Linear の具体的な挙動は未検証)。
  - bridge が自分のコメントに反応してしまう → bridge はコメントを読んでトリガーにしないので起きない。コメントの `[bridge]` は、人と Dispatcher が見分けるための目印。
- 本文に入れる目印(例: `dispatched-by: grok`)は偽装を防ぎません。書ける人なら誰でも付けられるからです。認可には使わず、記録のためのメモとしてだけ扱います。

### 信頼境界と起票後の改変検出(検品#10 指摘2)

creator の許可リストは「誰が issue を作ったか」しか見ません。許可された creator が作った issue に、別のメンバーが後から `agent-task` を付けたり説明欄を書き換えたりしても、creator ID は許可リストに入ったままです。そこで信頼境界を次のように定め、2 つの仕組みを重ねます。

**信頼境界の定義**: 実行してよいのは、「creator」「`agent-task` を付けた人」「説明欄を最後に書き換えた人」が全員 `BRIDGE_LINEAR_ALLOWED_CREATORS` に入っている issue だけです。対象 project(team)に編集権限を持つ人は全員、信頼境界の内側にいるものとして扱います。許可リストにない人が編集権限を持っているなら、その人が書き換えられない前提は成り立ちません。

1. **起動時の検査(fail closed)**: `doctor.py --check-linear` と bridge の起動処理で、対象 team の有効メンバー(guest を含む。無効化されたユーザーは除く)を取得します。許可リストにないメンバーが 1 人でもいれば、**bridge は起動しません**(以前の設計の「警告」から変えました)。メンバーを増やすときは、その人を許可リストに入れて信頼境界に含めるか、bridge 専用の team を分けるかを本人が決めます。取得に失敗したときも起動しません。
2. **実行直前の履歴照合(fail closed)**: ラベルを外す前に `issue.history`(10 章で実在と形を確かめる)を読み、次をすべて確かめます。1 つでも満たさない、または履歴を読めないときは実行しません。
   - `agent-task` を足した履歴(`addedLabelIds` に `agent-task` のラベル ID が入っている最新の 1 件)があり、その `actor.id` が許可リストに入っている。
   - その時点より後に、説明欄・タイトル・team・project を変えた履歴がない。
   - creator から現在までに説明欄を変えた履歴の `actor.id` がすべて許可リストに入っている。
   - 履歴の `actor` が null のもの(連携機能や自動化による変更など)がない。null は「誰か分からない」として拒否します。
3. **本文ハッシュの照合(履歴の補強)**: 2 段階起票の 2 段目で、Dispatcher は `agent-task` を付ける直前に取り直した説明欄の SHA256(UTF-8、Linear が返したそのままのバイト列)を、`[dispatcher] body-sha256: <hex>` という 1 行のコメントにします。bridge は、ラベルを外した後に取り直した説明欄の SHA256 がこのコメントの値と一致することを確かめます。コメントの作者が許可リストにない、コメントが 2 件以上ある、値が一致しない、のどれかなら実行しません。
   - このコメントも書ける人なら誰でも書けるので、ハッシュは単独では認可になりません。役割は、2 の履歴照合で見落とした変更(履歴に残らない種類の変更など)を拾うことです。認可の根拠は 1 と 2 です。
   - `updatedAt` は照合に使いません。コメントやラベルの付け外しでも変わるので、本文の改変を区別できないからです。

拒否したとき: ラベルは外したまま(処理済みの印。もう一度拾わない)にし、`[bridge] rejected: trust check failed (<理由>)` をコメントして Canceled にします。理由には actor の ID と変更されたフィールド名だけを書き、本文は書きません。再実行したいときは、本人か Dispatcher が新しい issue として起票し直します。

## 5. 認証

選択肢:

| 方式 | 長所 | 短所 |
|---|---|---|
| 個人用 API キー(推奨。まずはこれ) | 発行が簡単。GraphQL に `Authorization: <key>` を付けるだけ | 本人として動く(コメントの著者が本人になる)。権限とチームを絞れるかは未検証 |
| 独自の OAuth アプリ(actor=application) | コメントや状態変更の著者がアプリになり、人と区別できる | アプリの登録、token の更新、redirect の扱いが必要。構成が重い |
| Grok Bot コネクタの OAuth を使い回す | — | Mac からは使えない(token が外に出せない)。採用しない |

鍵の置き場所と運用:

- 鍵は Mac の `~/.config/slack-bridge/linear.env`(`chmod 600`)にだけ置き、`LINEAR_API_KEY=` で渡します。launchd は plist の中で `set -a; . linear.env` を実行して環境変数として読みます(既存の plist と同じやり方)。plist、リポジトリ、Issue、Linear、Slack、Grok Bot、チャットには書きません。
- bridge は鍵をログや例外メッセージに出しません(`linear()` の例外にはステータスと GraphQL のエラーコードだけを入れる)。`doctor.py` は値を出さず、キーがあるかどうかだけを報告します(既存の方針どおり)。

### 子プロセスへの鍵の継承を防ぐ(検品#10 指摘1)

現行の `run_task` は、子 agent の環境を `env = dict(os.environ, CROSS_HARNESS_PEER="1")` で作っています(f688563 でも、この改訂時点の main `6e556ed` でも `slack-bridge/bridge.py` 233 行)。launchd が `LINEAR_API_KEY` を bridge の環境変数として読ませると、このままでは鍵が agent(`claude -p`、`codex exec`、`agy` など)の subprocess にそのまま引き継がれます。agent は外部の入力(契約本文)に従って動くので、鍵が見える状態にしてはいけません。

要件:

1. 子 agent の環境は、新しい関数 `agent_env(environ)` だけで作ります。233 行はこの関数の呼び出しに置き換えます。bridge から起動するほかの subprocess のうち、契約の内容に従って動くもの(cursor の `--help` 確認を含め、agent のバイナリを起動するものすべて)にも同じ関数を使います。
2. `agent_env` は `os.environ` をコピーし、次に当てはまるキーを**値に関係なく**取り除きます。
   - 名前が `LINEAR_` で始まるもの(大文字小文字を区別しない)。`LINEAR_API_KEY` のほか、将来足す `LINEAR_OAUTH_TOKEN`、`LINEAR_WEBHOOK_SECRET` なども含む。
   - 名前が `BRIDGE_LINEAR_` で始まるもの(team、project、許可リストなど。秘密ではないが agent には要らない)。
   - 明示的な除外リスト `AGENT_ENV_DENY`(初期値は上の 2 つの接頭辞)。Linear 以外の鍵を後で足すときもここに足す。
   - 除外の判定はキーの名前だけで行います。値の中身を見て判定する処理は作りません(漏れを見落とす原因になるため)。
3. 鍵の値そのものが、別名の環境変数(例: 本人が `linear.env` に誤って別の名前で書いた場合)に入っていないことも確かめます。`agent_env` は、取り除く前の `LINEAR_API_KEY` の値と同じ値を持つキーが残っていたら、それも取り除き、stderr にキーの名前だけを 1 行出します。
4. `CROSS_HARNESS_PEER="1"` など、今 233 行で足している値は今のまま足します。GitHub 経路(`BRIDGE_TRANSPORT=github`)でも同じ関数を通しますが、Linear の変数がもともとないので動きは変わりません。
5. launchd 側でも、Linear 用のジョブだけが `linear.env` を読みます。GitHub 用の plist には `linear.env` を読ませません(多重の防御。1〜4 が主な対策)。

回帰テストは 7 章のテスト 13・14 です。

本人に必要な操作(この工程では実行しません。承認後に本人が行います):

1. Linear の設定 → Security & access → Personal API keys で、`mac-mini-bridge` という名前のキーを作る。権限とチームを選べるなら、team Ca1yam、読み書き、管理権限なしにする。
2. キーを Mac に届ける。経路はチャットやクラウドを通らないものに限る(tailnet 経由の SSH アプリか Screens で Mac に入り、`umask 077; cat >> ~/.config/slack-bridge/linear.env` に貼り付ける)。キーを Grok Bot や Slack に貼らない。
3. 漏れた疑いがあるときは、Linear でそのキーを revoke してから作り直す。

## 6. ポーリング

- webhook は使いません(Mac に受け口を開けないため)。
- 間隔: Linear 側のプロセスだけ `BRIDGE_POLL_SECONDS=60` にします(env はプロセスごとに分かれているので、GitHub 側の 20 秒はそのまま)。
- 問い合わせ: issues を絞る条件は `team.key = CA1`、`project.id = <BRIDGE_LINEAR_PROJECT>`、`labels.name = agent-task`、`state.type ∉ {completed, canceled}`、`first: 20` です。取るフィールドは `id identifier number description creator{id} labels{nodes{id name}} state{type}`。`number` の昇順で処理します(304 行と同じ)。
- 重複実行の防止:
  1. 実行前にラベルを外し、取り直して消えたことを確かめる(3 章)。確かめられなければ実行しない。
  2. Linear 側のプロセスは `linear.lock` を `LOCK_NB` で取り、取れなければ終了する(手で起動した 2 つ目のプロセスを防ぐ)。
  3. 共有の `run.lock` で、agent の実行を 1 本ずつにする(1 章)。
- レート制限: HTTP 429、または GraphQL の `errors[].extensions.code` が `RATELIMITED` のときは、次の poll まで待つ時間を倍にしていきます(上限 15 分)。理由は stderr に 1 行出します。1 回の poll で使うリクエストは、一覧 1 回と、実行する issue 1 件あたり数回です(ラベル削除、取り直し、状態変更 2 回、コメント 2〜3 回)。Linear の具体的な上限値は未検証です。
- 失敗時の扱い(取得できないことを「タスクなし」として扱わない):
  - HTTP エラー、タイムアウト、`errors` が空でない、`data.issues.nodes` がない、のどれかなら例外を投げる。`main` の 323–324 行が stderr に出し、ループは続く。
  - 例外が出た poll では一件も実行しない。ラベル削除が失敗した issue も実行しない。
  - 最後に成功した時刻、最後のエラー、連続失敗回数を `~/.local/state/slack-bridge/linear-health.json` に書き、`doctor.py` で読めるようにする。
  - 実行後のコメント投稿や状態変更の失敗、および各遷移の間でのクラッシュは、下の「状態遷移ごとの失敗と回復」で扱う。

### 状態遷移ごとの失敗と回復(検品#10 指摘3)

以前の設計では、ラベル削除と In Progress 更新の間で bridge が止まると、issue はラベルなしで元の状態(Todo/Backlog)に残り、「In Progress かつ結果コメントなし」という blocked 判定に当たりませんでした。結果コメントの後で Done への更新に失敗した場合も、結果コメントがあるので同じ判定から漏れました。これを、(a) Mac 側の作業記録(journal)、(b) 遷移ごとに冪等な再試行、(c) Linear 側だけを見る判定の 3 つで塞ぎます。

**journal**: `~/.local/state/slack-bridge/linear-journal.json`。issue の ID ごとに `{identifier, task_id, phase, status, result_path, attempts, last_error, updated}` を持ちます。書き込みは一時ファイルに書いて `fsync` してから `os.replace` で置き換えます。journal の更新は `linear.lock` を持つプロセスだけが行います。結果の全文は `~/.local/state/slack-bridge/linear-results/<task_id>.txt` に保存し、journal にはそのパスだけを書きます。

**遷移の順番と phase**(各遷移の前に journal へ phase を書く。phase は前にしか進まない):

| # | phase(書いてから行う) | 行う操作 | 冪等にする方法 |
|---|---|---|---|
| T0 | `claiming` | 4 章の履歴照合 → `agent-task` を外す | 外す前に取り直し、すでにラベルがなければ外したとみなす |
| T1 | `claimed` | 取り直してラベルが消えたこと、本文ハッシュ(4 章)を確かめる | 読み取りだけ |
| T2 | `started` | 状態を In Progress にし、`[bridge] claimed <task_id>` を親コメントにする | 状態は ID 指定なので何度送っても同じ。コメントは、同じ `<task_id>` を含む `[bridge]` コメントがすでにあれば投稿しない |
| T3 | `running` | `run_task` を実行する | 再実行しない(下の回復表) |
| T4 | `finished` | 結果を `result_path` に保存し、journal に `status` を書く | ローカルのみ |
| T5 | `reported` | 結果コメント(`[bridge] result <task_id>` で始まる)を返信として投稿する | 投稿前にコメント一覧を取り、同じ先頭行の返信があれば投稿しない |
| T6 | `closed` | Done/Canceled にする(`needs-approval` ならラベルを付けて In Progress のまま) | 状態とラベルは ID 指定なので何度送っても同じ。成功したら journal から消す |

**API 呼び出しの失敗(プロセスは生きている)**: その遷移を失敗として journal の `attempts` と `last_error` を更新し、次の poll で同じ phase から再試行します。待ち時間は 6 章のレート制限と同じく倍々(上限 15 分)です。T0〜T2 の失敗で agent を走らせることはありません。T5・T6 の失敗では agent を再実行せず、保存した結果を使って投稿だけをやり直します。`attempts` が 10 回を超えた issue は再試行をやめ、`linear-health.json` に `stuck` として載せます(`doctor.py` と 8 章の Dispatcher 判定で拾う)。

**クラッシュ後の回復**: bridge は起動するたびと、毎回の poll の最初に、journal に残っている issue をすべて取り直してから新しい issue を拾います。回復を終えるまで新しい issue は実行しません。

| journal の phase | Linear 側の状態 | 回復の手順 |
|---|---|---|
| `claiming` | ラベルがまだある | まだ何もしていない。journal から消し、通常の流れで拾い直す |
| `claiming` | ラベルがない | T0 は成功していた。`claimed` として T1 から続ける |
| `claimed`/`started` | 問わない | agent はまだ走っていない。T1 の確認をやり直し、通れば T2 から続ける。T1 で拒否になれば 4 章の拒否処理をする |
| `running` | 問わない | agent の結果は分からない。**再実行しない**。`blocked (bridge crashed during run)` を status として T5・T6 を行う(Canceled)。コメントには worktree のパスと branch 名を書き、worktree は消さない |
| `finished` | 問わない | `result_path` から結果を読んで T5 から続ける。ファイルがなければ `running` と同じ扱いにする |
| `reported` | 問わない | T6 から続ける |
| journal にない | ラベルなし、状態が completed/canceled 以外、`[bridge] claimed` コメントがあり、`[bridge] result` コメントがない | journal が失われた場合。agent が走ったかどうか分からないので `running` と同じ扱いにする |
| journal にない | ラベルなし、状態が completed/canceled 以外、`[bridge] result` コメントがある | コメントの 1 行目から status を読み、T6 だけを行う |

最後の 2 行のために、bridge は poll のたびに「対象 project で、ラベルがなく、状態の type が completed/canceled 以外で、`[bridge]` コメントがある issue」も 1 回のクエリで取ります(`first: 20`)。`[bridge]` コメントが 1 つもない、ラベルのない issue は Dispatcher の起票途中(2 段階の 1 段目)と区別できないので、bridge は触らず、8 章の Dispatcher 側の判定に任せます。

**Dispatcher 側の blocked 判定(Linear だけを見る。bridge が完全に止まっていても働く)**:

- (B1) Dispatcher が `agent-task` を付けた issue で、10 分たってもラベルが付いたまま → bridge が拾っていない(停止、または起動時検査で起動していない)。
- (B2) Dispatcher が `agent-task` を付けた issue で、ラベルがなく、状態の type が completed/canceled 以外、`[bridge] result` コメントがないまま、ラベルを付けてからタイムアウト + 10 分を過ぎた → 状態を問わず blocked。以前の「In Progress かつ」という条件は外します(T0 と T2 の間で止まった場合を拾うため)。
- (B3) `[bridge] result` コメントがあるのに、10 分たっても状態が Done/Canceled にならない(`needs-approval` を除く) → 「状態更新が止まっている」として報告し、status はコメントの 1 行目を使う。
- Dispatcher は、どの issue に `agent-task` を付けたかを自分で覚えています(2 段階起票の 2 段目)。B1〜B3 はその一覧だけを対象にするので、起票途中のラベルなし issue を誤って blocked にしません。

テストは 7 章のテスト 19〜26 です。

## 7. テスト計画

### ユニットテスト(`slack-bridge/test_bridge.py` に追加。`bridge.linear` をモックする)

1. `load_config` で linear 用の必須キーが欠けていると `SystemExit` になる。未知の transport は今のまま拒否される。
2. 試験で取り直した本文(付録 A の refetched)を `parse_contract` に通すと、4 キーが読め、本文が `Goal:` で始まる。
3. 正規化: CRLF、空白だけの区切り行、先頭の空行、末尾の改行なし、ヘッダーと本文の間の空行が 3 つ。どれも同じ結果になる。
4. ヘッダーの値に `\` や `[` などがあると `rejected` になる。
5. `linear_tasks`: 許可されていない creator、ラベルなし、別の project の issue は除かれる。
6. `poll_linear_once` の呼び出し順: ラベル削除 → 取り直し → In Progress → `run_task` → Done。削除か取り直しが失敗したら `run_task` を呼ばない。
7. 状態の対応: `done` → Done、`failed (exit 1)`/`rejected`/`blocked (no route)` → Canceled、`needs-approval` → ラベルを付けて In Progress のまま。
8. HTTP 200 で `errors` が返ったときは例外になり、空の一覧として扱わない。429 のときは待ち時間が延びる。
9. コメント: 1 件目は親コメント、2 件目以降は `parentId` 付き。すべて `[bridge]` で始まり、`REPLY_LIMIT` で切られる。
10. `run.lock`: 2 つ目のプロセスは 1 つ目が終わるまで worktree を作らない(一時ディレクトリで flock を使って確かめる)。
11. 例外メッセージや stderr に `LINEAR_API_KEY` の値が出ない。
12. 既存の GitHub と Slack のテストがすべて変更なしで通る(`python3 -m unittest slack-bridge/test_bridge.py`)。

子プロセスの環境(検品#10 指摘1):

13. `run_task` が agent を起動するとき、`subprocess.run` に渡る `env` に `LINEAR_API_KEY`、`LINEAR_` / `BRIDGE_LINEAR_` で始まるキー、`LINEAR_API_KEY` と同じ値を持つ別名のキーが**含まれない**。`os.environ` にダミーの鍵(`lin_api_TEST_DO_NOT_USE` など)を入れ、`subprocess.run` をモックして渡された `env` を調べる。`CROSS_HARNESS_PEER=1` と `PATH`、`HOME` は残っている。route が複数ある場合(フォールバック)と cursor の `--help` 確認でも同じことを確かめる。
14. 実際の子プロセスで確かめる: `build_command` を差し替えて `[sys.executable, "-c", "import os,json; print(json.dumps(sorted(os.environ)))"]` を走らせ、出力に Linear 関連のキーがなく、ダミーの鍵の値も出力のどこにも現れない。233 行を `dict(os.environ, ...)` に戻すとこのテストが落ちることを、実装時に一度確かめる。

信頼境界(検品#10 指摘2):

15. 起動時検査: 許可リストにない有効メンバー(guest を含む)がいる、またはメンバー一覧を取れないと、bridge が起動しない(`SystemExit`)。無効化されたユーザーは数えない。
16. 履歴照合: (a) creator は許可済みだが `agent-task` を付けた actor が許可リスト外、(b) ラベルを付けた後に説明欄が変更された、(c) 説明欄を変えた actor が許可リスト外、(d) actor が null、(e) 履歴を取れない。どれも `run_task` を呼ばず、`rejected: trust check failed` をコメントして Canceled にする。
17. 本文ハッシュ: `[dispatcher] body-sha256:` が一致しない、2 件ある、作者が許可リスト外、ない。どれも実行しない。一致して履歴も正しいときだけ実行する。
18. 拒否時のコメントに本文や鍵が入らない。

状態遷移の失敗と回復(検品#10 指摘3。`bridge.linear` のモックで特定の呼び出しを失敗させ、プロセスの停止は phase を書いた直後に例外で抜けることで再現する):

19. T0(ラベル削除)の API が失敗: `run_task` を呼ばない。journal は `claiming` のまま。次の poll で取り直し、ラベルが残っていれば拾い直し、なければ T1 から続く。
20. T0 の後、T2(In Progress)の前で停止: 再起動後の回復で T1 から続き、In Progress と `[bridge] claimed` コメントが 1 件だけになる。agent は 1 回だけ走る。
21. T2 の状態変更またはコメントが失敗: 次の poll で再試行し、コメントは重複しない。T2 が終わるまで `run_task` を呼ばない。
22. `running` で停止: 再起動後に agent を再実行せず、`blocked (bridge crashed during run)` の結果コメントを投稿して Canceled にする。worktree は残る。
23. T5(結果コメント)が失敗: 保存した結果から投稿をやり直し、agent は再実行しない。投稿が成功していたのに応答が失われた場合(モックで「投稿はされたが例外」にする)も、結果コメントは 1 件だけになる。
24. T6(Done/Canceled)が失敗: 次の poll で状態だけをやり直す。`attempts` が上限を超えると `linear-health.json` に `stuck` が出る。
25. journal が失われた: Linear 側に `[bridge] claimed` だけがある issue は 22 と同じ扱い、`[bridge] result` がある issue は状態だけを直す。`[bridge]` コメントがないラベルなし issue には触らない。
26. Dispatcher の判定規則(B1〜B3)を表にした fixture で、T0 と T2 の間で止まった issue(ラベルなし・Todo)が B2 に、結果コメントはあるが Done になっていない issue が B3 に当たる。これは判定ロジックを `slack-bridge/linear_watch.py`(新規)のような純粋関数にして、そこでテストする。

モックのテストは、Linear API の実際の形(10 章)を確かめた後で、記録した実際の応答(鍵や個人情報を除いたもの)を fixture にして書きます。10 章の smoke を通る前に、モックのテストが通ったことを API 契約の証拠として扱いません(検品#10 指摘4)。

### 段階的な導入(各段階で承認を得る)

1. PR を review し、merge する(本人の承認)。
2. 本人が API キーを作って Mac に置く(5 章)。Linear に `agent-task` と `needs-approval` のラベルを作る(本人か Dispatcher。承認が要る)。
2a. 10 章の API 検証と smoke を行い、受け入れ条件 S1〜S8 をすべて満たす(検品#10 指摘4)。満たすまで、bridge の Linear 経路は実装を merge しないか、merge しても launchd に登録しない。
3. 読み取りだけの確認: `python3 slack-bridge/doctor.py --check-linear`(viewer、team、project、状態 ID を解決できるか)。
4. bridge-test project で 1 件だけ: Dispatcher が 2 段階で害のない契約を起票する(例: agy で `git log -1 --oneline` を報告するだけ)。launchd は使わず、前景で 1 回だけ poll して終わる。`python3 -c 'import bridge; bridge.poll_linear_once(bridge.load_config())'`(env は `linear.env` から読む)。確かめること: ラベルが外れた、In Progress から Done に移った、コメントが親と返信の形になった、worktree の名前が `bridge-linCA1-…` になった。
5. `com.maylac.linear-bridge` を launchd に登録する(新しいジョブなので既存 bridge の再起動ではない。ただし設定変更なので承認を得る)。bridge-test でもう 1 件確かめる。
6. 本番用 project に切り替える: `BRIDGE_LINEAR_PROJECT` を変え、Linear 側のジョブだけを再起動する(実行中の agent がいないことを確かめてから。承認が要る)。
7. GitHub 側のプロセスを、空いているときに再起動して `run.lock` を有効にする(Hard Stop。本人の個別承認)。

### 戻し方(GitHub 経路だけに戻す)

1. Dispatcher が Linear への起票をやめる(指示の文書を元に戻す)。
2. `launchctl bootout gui/$(id -u)/com.maylac.linear-bridge` を実行し、plist を外す。実行中の agent がいるときは止まるので、実行中でないことを確かめるか、本人の承認を得てから行う。
3. ラベルが外れたまま In Progress に残った Linear の issue には、Dispatcher が理由をコメントして Canceled にする。
4. GitHub 側のプロセスは一度も止めていないので、ほかに作業はありません。コードを戻す場合は PR を revert します。linear 経路は付け足しただけなので、GitHub の動作は変わりません(テスト 12 で保証する)。

### 再起動と承認の境界

- `com.maylac.slack-bridge`(GitHub)の bootout、kickstart、再起動は、どれも Hard Stop です。本人の個別承認が要ります。
- `com.maylac.linear-bridge` も dispatch bridge なので同じ扱いです。最初の登録(5)だけは、何も止めないので設定変更の承認で足ります。
- merge しても、動いているプロセスは古いコードのまま動き続けます(Python は起動したときにコードを読む)。merge しただけで再起動は起きませんが、新しいコードが効くのは再起動した後です。

## 8. 運用文書の更新点(一覧だけ。書き換えはしない)

`docs/grok-bot/dispatcher-instructions.md`:

- 3 行目: 「GitHub Issue の作業契約」→ GitHub Issue か Linear issue。GitHub が正本であることを書き足す。
- 7 行目: 役割の「Issue 起票」に Linear を足す。
- 14–16 行目(起票): Linear の起票手順を足す(専用 project、ラベルなしで作成 → `get_issue` でヘッダー 4 行を照合 → `agent-task` を付ける)。どちらの経路を使うかの規則(既定は GitHub)も書く。
- 18–30 行目(テンプレート): Acceptance の `  - ` を `A1:` 形式に変える(Linear では `-` が `*` に変わり、空行が入る)。バックスラッシュとトリプルバッククォートを禁止すると書き足す。
- 32 行目: `model:` と `fallback:` の扱いは今のまま。
- 45 行目: 結果コメントは `[bridge]` で始まり、Linear では親コメントへの返信になる。
- 49 行目: Linear の `needs-approval` は、ラベル付きで In Progress のまま。
- 51 行目: 6 章の blocked 判定 B1〜B3 を足す(検品#10 指摘3。以前の「In Progress でラベルがなく、結果コメントもない」という条件は、状態を問わない B2 に置き換える)。Linear の 2 段階起票の 2 段目で `[dispatcher] body-sha256:` コメントを付ける手順も足す(4 章、検品#10 指摘2)。

そのほかの文書:

- `docs/grok-bot/README.md` 3・17・23・28 行目: 図と説明に Linear の経路を足す。
- `docs/grok-bot/activation-plan.md` 13 行目と 178 行目付近: Linear の smoke 手順と、未確認であることを書き足す。
- `slack-bridge/README.md` 25–26 行目: 契約例の `  - ` を `A1:` にする。`doctor.py --check-linear` の説明を足す。
- `~/AGENTS.md`(ホーム。repo の外): 「One dispatch = one GitHub issue」の節に Linear の併用を足す(ホームのファイルなので、別の承認を得てから変える)。
- Grok Bot 側の Dispatcher 指示(GitHub Issue 経由で配っているもの): 上の dispatcher-instructions.md と同じ箇所を変える。

## 9. 未検証の点

- Linear 側で、ラベル付きの issue を作る、ラベルを付け外しする、状態を変える、`parentId` で返信する。報告では API の形は分かっているが、どれも試していない。
- Linear GraphQL API の具体的な仕様(エンドポイント、`Authorization` ヘッダーの形、レート制限の値、`RATELIMITED` のコード名、`issueRemoveLabel` 相当の mutation があるか)。この作業ではネットワーク越しに確かめておらず、設計は一般的な GraphQL の扱いを前提にしている。
- 個人用 API キーで権限やチームを絞れるか。Mac から Linear に届くか(ネットワークと認証の制約は推測しない)。
- ヘッダーの値に `_` や `*` などが入ったときに、Linear がエスケープしたりリンクにしたりするか(試験の値にこれらの文字は入っていなかった)。
- コメントの中の複数行コードブロック(`run_task` の 260 行が出す ```` ``` ```` 囲み)が保たれるか(コメントの試験は 1 行だけだった)。
- 連携機能(メール、フォーム、Slack)で作られた issue の creator がどうなるか。
- Grok Bot の報告に書かれた Linear 側の事実(workspace と team の構成、状態の一覧、creator の ID、コメント API の挙動)。コード屋が独自に確かめたのは、付録 A の本文 2 件と SHA256 だけ。
- `issue.history` で、ラベルの追加者、説明欄の変更、actor を取れるか(4 章の履歴照合の前提)。team メンバーの一覧で guest と無効化ユーザーを区別できるか。

これらは 10 章の手順で、実装の前に確かめます。

## 10. 実装前の API 検証と smoke 受け入れ条件(検品#10 指摘4)

7 章のユニットテストは `bridge.linear` をモックするので、Linear の実際のスキーマや mutation が設計どおりかは確かめられません。そのため、**実装に入る前に**次の検証を行い、結果を記録します。この改訂(2026-11-01)では、手順と受け入れ条件を書いただけで、検証そのものは行っていません。Linear への書き込みを含むので、実行には本人の承認が要ります(7 章の段階 2a)。

### 10.1 読み取りだけの検証(V1〜V5)

使う鍵は 5 章で置いたものです。鍵はコマンドラインに書かず、`linear.env` から環境変数で読みます。応答は `~/.local/state/slack-bridge/linear-verify/` に保存し(`chmod 700`)、鍵と個人のメールアドレスを除いてから 7 章の fixture に使います。

- V1 エンドポイントと認証: `https://api.linear.app/graphql` に `{ viewer { id name } }` を送り、`Authorization` ヘッダーの形(`<key>` か `Bearer <key>` か)と、返る viewer の ID が 4 章の creator ID と一致するかを記録する。
- V2 スキーマの取得: introspection(`__schema` / `__type(name: "Mutation")`)で、次の実在と引数の型を記録する。introspection が無効なら、公式のスキーマ定義(Linear が公開している SDL)を取得し、取得元の URL と日付を記録する。
  - ラベルの付け外し: `issueRemoveLabel` / `issueAddLabel` があるか。なければ `issueUpdate(input: {labelIds})` で全体を置き換える方式になるが、その場合は同時に付いた別ラベルを消しうるので、取り直し → 置き換え → 取り直しの手順を設計に足す。
  - 状態変更: `issueUpdate(id, input: {stateId})`。
  - コメント: `commentCreate(input: {issueId, body, parentId})` と、コメント一覧(`issue.comments`)で `parent` と `user` が取れるか。
  - 履歴: `issue.history` の `actor`、`addedLabelIds`(またはそれに当たるフィールド)、`updatedDescription`(または説明欄の変更を示すフィールド)、`createdAt`。
  - メンバー: `team.members` で `active`、`guest` が取れるか。
  - 一覧の絞り込み: 6 章の filter(team、project、labels、state.type)がそのまま書けるか。
- V3 レート制限の仕様: 公式ドキュメントの記載(リクエスト数と complexity の上限、期間)と、応答ヘッダー(`X-RateLimit-*` など、実在するもの)を記録する。上限に達したときの HTTP ステータスと `errors[].extensions.code` の実際の値を、ドキュメントか実際の応答で確かめる(実際に上限まで叩くことはしない)。6 章の `RATELIMITED` と待ち時間の規則を、記録した値に合わせて直す。
- V4 エラーの形: 存在しない issue ID を読む、存在しない stateId で `issueUpdate` するといった、副作用のない失敗を起こし、HTTP 200 + `errors` になるのか、別のステータスになるのかを記録する。
- V5 権限: 個人用 API キーで権限やチームを絞れるかを、作成画面と viewer の応答から記録する。

### 10.2 書き込みを含む smoke(bridge-test project だけで行う)

害のない issue を 1 件ずつ使い、終わったら Canceled にします(削除はしない)。

- S1 成功の流れ: ラベルなしで作成 → 取り直し → `agent-task` を付ける → `[dispatcher] body-sha256:` コメント → ラベルを外す → 取り直してラベルが消えたことを確認 → In Progress → 親コメント → `parentId` 付きの返信 → Done。それぞれの mutation の応答と、取り直した状態が設計どおりであること。
- S2 ラベルの付け外しが冪等か: すでにないラベルを外す、すでにあるラベルを付ける、の応答(エラーか成功か)を記録し、6 章の T0 の冪等性の前提が成り立つこと。別のラベルが付いている issue でラベルを外しても、別のラベルが残ること。
- S3 部分失敗 1(ラベル削除の後で止まる): ラベルを外したところで手順を止め、issue がラベルなし・Todo のまま残ることを確かめる。そのうえで、6 章の回復手順(journal が `claiming`/`claimed` の場合)を手で再現し、T1 から続けて In Progress とコメント 1 件で終わること。
- S4 部分失敗 2(状態変更の失敗): 存在しない stateId で `issueUpdate` を送ってエラーになることを確かめ、ラベルを外した状態と他のフィールドが変わっていないこと。続けて正しい ID でやり直して成功すること。
- S5 部分失敗 3(結果コメントの後で止まる): 結果コメントを投稿したところで止め、Done にしないまま残す。6 章の回復(journal なしで `[bridge] result` がある場合)で、状態だけが直ること。B3 の判定に当たること。
- S6 履歴: S1 の issue の `history` で、ラベルを付けた actor、説明欄の変更、actor が null にならないことを確かめる。説明欄を手で 1 回書き換え、その変更が履歴に actor 付きで出ること(4 章の照合がこの変更を拒否できること)。
- S7 コメントの体裁: 複数行のコードブロック(```` ``` ```` 囲み)と `REPLY_LIMIT` 近い長さの返信が、取り直したときに保たれていること(9 章の未検証点)。
- S8 子プロセスの環境: 前景で 1 回だけ poll するとき(7 章の段階 4)、agent に `env | cut -d= -f1` を報告させる無害な契約を使い、`LINEAR_` で始まるキーがないこと(検品#10 指摘1)。

### 10.3 受け入れ条件

- V1〜V5 と S1〜S8 の結果を、`docs/specs/` に新しいファイル(例: `2026-11-xx-linear-api-verification.md`)として記録し、各項目に「確かめた / 設計を直した / 未確認」のどれかを書く。鍵とメールアドレスを除いたものだけを載せる。
- S1〜S8 がすべて「確かめた」になっていること。V2 で mutation の形が設計と違った場合は、この設計書の 3・4・6 章を直す PR を先に merge してから実装に入る。
- 確かめた応答から作った fixture が、7 章のユニットテストで使われていること。
- 「未確認」が残ったまま実装に入らない。どうしても確かめられない項目は、本人が承認したうえで、その項目に頼らない設計(例: 履歴が取れないなら、許可リスト外の編集者がいない単独メンバー team に限る)に変える。

## 付録 A: 試験本文の再計算

依頼文にある 2 つの JSON 文字列をそのままファイルに保存し、`json.loads` で 1 回デコードしてから、UTF-8 で SHA256 を計算しました。

```
sent      660 bytes  2bd8196675754dfc0b04e4fe43dfa6910af099f5dbdadd29c3bd60212dde9930
refetched 661 bytes  6d7af6b3c630f66179e898af0346a9a017bb0aa6086f49cda7c782b9835636ef
```

どちらも依頼文の値と一致しました。現行(HEAD)の `bridge.parse_contract` は、どちらの本文からも `{'agent': 'claude', 'repo': '<home>/workspace/maylac/agents-setup', 'model': 'claude-opus-5-5', 'fallback': 'off'}` を返し、本文の 1 行目は `Goal: 改行保持の試験。これは実行契約ではない。` でした。
