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
  - 起票後に説明欄が書き換えられる → bridge は処理する時点の本文を使う。workspace のメンバーが本人だけである限り、書き換えられるのも本人だけ。`doctor.py --check-linear` で workspace の有効メンバー数を見て、2 人以上なら警告する。メンバーを増やすときは、この設計を見直すことを条件にする。
  - 連携機能(メールからの起票、フォーム、Slack 連携など)で作られた issue → creator は連携側のユーザーになるので許可リストで弾かれる(Linear の具体的な挙動は未検証)。
  - bridge が自分のコメントに反応してしまう → bridge はコメントを読んでトリガーにしないので起きない。コメントの `[bridge]` は、人と Dispatcher が見分けるための目印。
- 本文に入れる目印(例: `dispatched-by: grok`)は偽装を防ぎません。書ける人なら誰でも付けられるからです。認可には使わず、記録のためのメモとしてだけ扱います。

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
  - 実行後にコメントの投稿に失敗した場合は、結果の全文を stderr に出し、issue は In Progress のまま残す。Dispatcher は「In Progress でラベルがなく、`[bridge]` の結果コメントもないまま、タイムアウト + 10 分を過ぎた issue」を blocked として報告する(8 章)。

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

### 段階的な導入(各段階で承認を得る)

1. PR を review し、merge する(本人の承認)。
2. 本人が API キーを作って Mac に置く(5 章)。Linear に `agent-task` と `needs-approval` のラベルを作る(本人か Dispatcher。承認が要る)。
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
- 51 行目: 「In Progress でラベルがなく、結果コメントもない」ままの issue を blocked として報告する規則を足す。

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

## 付録 A: 試験本文の再計算

依頼文にある 2 つの JSON 文字列をそのままファイルに保存し、`json.loads` で 1 回デコードしてから、UTF-8 で SHA256 を計算しました。

```
sent      660 bytes  2bd8196675754dfc0b04e4fe43dfa6910af099f5dbdadd29c3bd60212dde9930
refetched 661 bytes  6d7af6b3c630f66179e898af0346a9a017bb0aa6086f49cda7c782b9835636ef
```

どちらも依頼文の値と一致しました。現行(HEAD)の `bridge.parse_contract` は、どちらの本文からも `{'agent': 'claude', 'repo': '/Users/gotasasaki/workspace/maylac/agents-setup', 'model': 'claude-opus-5-5', 'fallback': 'off'}` を返し、本文の 1 行目は `Goal: 改行保持の試験。これは実行契約ではない。` でした。
