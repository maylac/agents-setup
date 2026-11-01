# スマホ発・Mac mini ハーネスの摩擦レス設計（Grok Bot / Claude Duet / Muse）

- 日付: 2026-11-01
- 状態: 設計案。コードと launchd は未変更。
- 対象: 「依頼 → 起票 → Mac mini で実行 → 検品 → 報告 → 承認」の往復を、スマホだけで完結させる。
- 前提: 利用者は PC を触らない。Mac mini が唯一の実行場所。GitHub の private queue `maylac/agent-tasks` が唯一の台帳。
- 姉妹文書: [承認ストレスを最小化する権限境界の設計](2026-11-01-approval-boundary-design.md)（ツール権限を設定で 0 にし、業務判断だけを人に残す）。

## 0. 結論

| 役割 | 担当 | 一言 |
|---|---|---|
| 司令塔（依頼を契約にして起票、結果を読み戻して報告） | **Grok Bot コード屋** | 今のまま。周辺の仕事を外して軽くする |
| 朝ブリーフ・検品・承認の運び屋 | **Claude Duet** | 低頻度・高価値だけ。Claude Code と同じ利用枠を食うので頻度を絞る |
| 個人用件（買い物・予約・リマインド） | **Muse** | 制御系に入れない。開発アイデアは Slack `#inbox` に落とすだけ |
| 決定的な処理（queue の一覧化、通知、再開） | **Mac mini の launchd と bridge** | LLM を使わず 0 トークンで動かす |
| 対話で直接やる作業（設計・調査・多 repo） | **Claude iOS の Remote Control** | `manual` 扱い。実装は worktree の host で |

要点は三つ。
1. 起票できる controller は同時に一つ（通常は Grok、Grok が止まったときだけ Duet）。bridge 側で owned files の重複を拒否し、二重編集を機械的に防ぐ。
2. 承認は人のタップだけ。通知は GitHub Mobile の push と Duet の二経路、返答は本人が GitHub Mobile から書く Issue コメント `APPROVED:` 一本に統一する。Bot には書かせない。
3. 追加 Grok Bot 3 体（検品係・運用ハブ・Bot設計係）の計画は取り下げる。Duet と Mac 側 publisher で同じ役割を、規約同意なしで満たす。

## 1. 現状と摩擦点（2026-11-01 観測）

| # | 観測 | 根拠 | 摩擦 |
|---|---|---|---|
| F1 | bridge は稼働中。今日 08:23〜11:54 に worktree `bridge-gh45`〜`gh55` の 11 本が作られた | `$HOME/.local/state/slack-bridge/worktrees` | なし（健全） |
| F2 | 許可 repo は `agents-setup` だけ | `BRIDGE_ALLOWED_REPOS` | Vantik（reskilling-os）の作業は Remote Control の手動セッション頼み |
| F3 | Grok の追加 3 Bot は規約同意待ちで未作成 | `docs/grok-bot/bot-roles.md` | 検品と運用ハブが人手か Grok 1 体の兼任 |
| F4 | 運用ハブ（issue 6）の更新は Grok の日次 routine 依存、初回 callback 未確認 | 同上 | 台帳の鮮度を Grok の稼働に賭けている |
| F5 | `needs-approval` は Issue に label が付くだけ。push 通知はなく、承認後の再開は再起票 | `bridge.py poll_github_once` | 承認 1 回に Grok との往復が 2〜3 回要る |
| F6 | Bot 間の引き継ぎで本文が欠落した（issue 5 の `[5件: ...]`） | `docs/grok-bot/README.md` 9 | 検品が原文に届かない |
| F7 | Remote Control host が 3 本。`agents-setup` host の stdout.log が 363 MB（監査 A10 未対応）。`vantik` host は `reskilling-os-rc` の trust 未承諾で起動失敗。`workspace` host は本日 13:11 作成 | `$HOME/.claude/remote-control/`、LaunchAgents | iPhone から Vantik を直接開けない。ディスクを食い続ける |
| F8 | Claude の 5 時間枠がボトルネック（監査 A7 / E） | `docs/harness-audit-2026-10-13.md` | Duet も同じ枠を消費する。設計で頻度を縛る必要がある |
| F9 | Remote Control のサンドボックス内では `gh`（keyring）と Codex（`auth.json` 読み取り拒否）が使えない | 本セッションの観測 | 本設計の実装は bridge 契約か通常セッションで行う |

## 2. 設計原則

1. **台帳は GitHub 一つ。** 依頼・契約・結果・承認・検品の記録はすべて `maylac/agent-tasks` の Issue に残す。チャットは入口と出口であって記録ではない。
2. **実行は Mac だけ。** Grok（xAI）、Duet（Anthropic）、Muse（Meta）の VM はどれも Mac の SSH 鍵・NAS 認証・API key を持たない。クラウド側は読む・起票する・通知するまで。
3. **controller は同時に一つ。** 起票は Grok コード屋。Duet は Grok が止まったときだけ `via: duet` を付けて起票する。bridge は owned files が重なる契約を機械的に拒否する。
4. **人の判断は人のタップだけ。** Bot のメッセージは承認にならない。承認の返答は Issue コメント `APPROVED: <正確な操作>` に統一し、本人の GitHub login で書かれたものだけを bridge が認める。Grok と Duet の connector は本人の account で動くので、GitHub からは人と Bot を区別できない。だから Bot には `APPROVED:` を書かせず、通知と下書きまでにする（7.2）。
5. **予算を分ける。** Grok Bot は独自の利用枠、Duet は Claude プランの枠（Claude Code と共有）、Mac の launchd は 0 トークン。頻繁なポーリングは Grok か launchd に、低頻度で判断が要るものだけ Duet に置く。
6. **通知は push 二経路。** GitHub Mobile（assignee 通知）と Duet（Gmail 経由）。どちらか一方が止まっても承認待ちを見落とさない。

## 3. 役割マトリクス

| 仕事 | Grok Bot | Claude Duet | Muse | Claude iOS RC | Mac（bridge / launchd） |
|---|---|---|---|---|---|
| 依頼の入口 | 主（文章・音声） | 予備 | 個人用件のみ | 手動作業 | — |
| 契約の起票 | 主 | Grok 停止時のみ | 禁止 | `manual` label | 重複 scope を拒否 |
| 実行 | 禁止 | 禁止 | 禁止 | 対話で実行 | 唯一の実行場所 |
| 監視・朝ブリーフ | 08:00 routine（差分要約） | 朝ブリーフ（Gmail の GitHub 通知から） | — | — | 30 分ごとに issue 6 を更新 |
| 検品 | 依頼の読み戻し | `VERIFIED:` コメント（別ベンダーで独立） | — | — | Codex / Cursor の読み取り専用レビュー |
| 承認の通知 | 会話で転送 | push | — | — | assignee 追加（GitHub Mobile push） |
| 承認の返答 | 通知と下書きまで（転記しない） | 通知と下書きまで（転記しない） | — | 本人が GitHub Mobile から `APPROVED:` をコメント | 本人 login の `APPROVED:` だけ検知して再開 |
| 個人用件 | — | 予定・メール | 主 | — | — |
| 秘密 | 持たない | 持たない | 持たない | Mac 上 | Mac 上 |

## 4. Grok Bot（司令塔）

Grok は今のまま司令塔にする。変えるのは周辺で、Grok が「読んで、起票して、報告する」以外をしなくて済むようにする。

### 4.1 追加 3 Bot の計画を取り下げる
- 検品係 → Claude Duet（5.4）と Mac 上の Codex / Cursor 読み取りレビュー。
- 運用ハブ → Mac 側 publisher（7.4）。Grok の routine は一覧を作らず、publisher が書いた issue 6 を読んで差分だけ報告する。
- Bot設計係 → 不要。役割はこの文書と `bot-roles.md` で固定する。
- 効果: 追加規約への同意という本人作業が消える。Grok は 1 体のまま。

### 4.2 引き継ぎは URL と SHA256 だけにする
- 本文を Bot 間で転記しない。`source issue` の URL、comment ID、UTF-8 SHA256 だけを渡す。
- 本文が必要な側（Mac 上の Claude / Codex / Cursor）は `gh api` で原文を取り、SHA256 を照合する。
- `dispatcher-instructions.md` の「`original_comment` に JSON で格納」の節を「URL と SHA256 のみ、本文は Mac で取得」に書き換える。F6 の欠落を根絶する。

### 4.3 許可 repo に `reskilling-os` を追加する
- `BRIDGE_ALLOWED_REPOS` に `$HOME/workspace/maylac/reskilling-os` を追加（bridge 再起動が要るので 9 の承認項目）。
- 追加後に smoke 契約 1 本（`Owned files: docs/` の無害な変更、`npm run lint` だけ）を通してから本番の依頼を流す。
- Vantik の本番確認は既存 skill `vantik-prod-verify` の手順を契約の Acceptance に書く。

### 4.4 Grok Skills は三つに絞る
| Skill | 入力 | 出力 |
|---|---|---|
| 状況 | なし | issue 6 の「判断待ち」「異常」「実行中」をそのまま 5 行以内で返す |
| 起票 | 依頼文 | `README.md` の契約形式で Issue 1 本。`Owned files` と `Acceptance` を必ず埋める |
| 承認案内 | 本人の返答 | 対象 Issue の URL と、そのまま貼れる `APPROVED: <操作>` の 1 行を返す。Grok 自身は Issue に書かない |

### 4.5 やらないこと
- クラウドで実装・修正しない。Issue 本文の要約転記をしない。issue 6 の本文を書き換えない（publisher の仕事）。

## 5. Claude Duet（朝ブリーフ・検品・承認の運び屋）

### 5.1 前提と、使えない場合の代替
- Duet は research preview で、US の Pro / Max / Ultra プラン、waitlist 招待制。account の email と端末の Apple / Google account の一致が条件。利用は Claude の 5 時間枠と週次枠を消費し、background の確認も課金対象。11/30 までの枠リセット 1 回が付く。
- 使えない間は、この章の仕事を Grok の 08:00 routine と GitHub Mobile 通知で代替する。設計は Duet なしでも成立する。

### 5.2 接続するもの、しないもの
- 接続する: Gmail（GitHub の通知メールを読む）、Google Calendar、Slack（`#inbox` 読み取り）。GitHub connector は Marketplace に有無を確認してから足す。
- 接続しない: SSH、NAS、Claude Code の Remote Control、`gh` のトークン。Duet は「読む・まとめる・本人が承認したものを送る」まで。

### 5.3 朝ブリーフ
- 07:30 JST に Mac の publisher が ops-hub issue にコメントを 1 本書く（本文は issue 6 の最新 snapshot の先頭 20 行）。コメントは GitHub からメールで届く。
- Duet の朝ブリーフが Gmail を読むとき、このメールが「判断待ち N 件、異常 M 件、実行中 K 件」として載る。
- Grok の 08:00 routine と内容が重なるが、経路が違う（Gmail と GitHub connector）ので片方が止まっても届く。

### 5.4 検品係
- 契約の `done` 後、Grok が Duet に「検品: issue URL、PR URL、期待する check」を渡す（Bot 間の直接連携が無いので、本人が Duet に 1 行転送する運用から始める）。
- Duet はクラウドのブラウザで PR の head、check、成果物リンクを開き、合否と根拠を `VERIFIED:` 形式で下書きする。
- 送信は Duet が本人の承認を求める。本人のタップが「人が検品結果を確認した」記録になる。Grok 製の下書きを Grok が採点する自己採点を避け、別ベンダーの独立確認になる。

### 5.5 承認の運び屋
- bridge が `NEEDS-APPROVAL:` をコメントすると GitHub からメールが届く。Duet はこれを「要承認」として push 通知する。
- Duet は Issue の URL と、そのまま貼れる `APPROVED: <操作>` の 1 行を添える。本人は GitHub Mobile を開いてその行をコメントする。bridge が本人 login の `APPROVED:` を検知して再開する（7.2）。Grok を経由しない最短経路。
- Duet に書かせない理由: Duet の送信は Duet 側の確認を通るが、GitHub に残るのは本人 account の投稿で、bridge からは Bot の投稿と区別できない。Bot 用の別 GitHub account を作れば Duet 経由の返答も許可できる（9 の判断項目）。

### 5.6 予備の司令塔
- Grok Bot が rate limit や障害で止まったときだけ、Duet が同じ契約形式で起票する。ヘッダに `via: duet` を足す（`parse_contract` は未知のヘッダ行を受け付けるので bridge の変更は不要）。
- 同じ job を Grok と Duet の両方が起票しても、bridge の scope 重複拒否（7.3）で 2 本目は `blocked (duplicate scope #N)` になる。

### 5.7 指示の単一ソース化
- `docs/grok-bot/dispatcher-instructions.md` を正本にし、Grok の説明欄と Duet 用 skill（`skills/phone-dispatcher/SKILL.md`）を同じ本文から生成する。Duet は Claude account の skill を引き継ぐので、契約形式・Hard Stop・報告形式を Grok と同じ言葉で持てる。

### 5.8 予算ガード
- Duet の background は朝ブリーフ 1 回とイベント駆動（メール到着）だけにする。定期ポーリングは Grok と launchd に置く。
- 検品は依頼時のみ。大きな生成物（資料・ダッシュボード）は Duet に頼まない。Claude Code の枠を守る。

## 6. Muse（個人用件専任）

### 6.1 制御系に入れない理由
- Muse の公開 connector に GitHub は無い（Notion・Slack・Asana・Dropbox・Zoom・Shopify・Stripe など）。US（18 歳以上）と Canada 向けで、WhatsApp・iOS・Android・web から使う。
- 第三の controller を増やすと二重編集の経路が増える。原則 3 に反する。
- Meta の VM に開発情報を置く理由が無い。

### 6.2 使い方
- 買い物・予約・リマインド・調べ物など、Mac を使わない個人用件を任せる。
- 開発のアイデアを思いついたら Muse に「メモ」と言い、Muse は Slack `#inbox` に 1 行投げる（Notion でも可）。`#agent-tasks` には書かせない。
- Grok の 08:00 routine が `#inbox` を読み、契約にできるものだけ本人に「起票しますか」と聞く。

### 6.3 使えない場合
- 何も失わない。`#inbox` は本人が直接書けばよい。

## 7. Mac mini 側の変更（決定的・低コスト）

すべて `slack-bridge/` と `launchd/` の範囲。bridge のテストに fake executable を使う既存方式で回帰テストを足す。

### 7.1 `needs-approval` で assignee を付ける（F5）
- `poll_github_once` の `needs-approval` 分岐で `gh issue edit <n> --add-assignee <login>` を実行する。login は `BRIDGE_APPROVAL_ASSIGNEE`（未設定なら何もしない）。
- GitHub Mobile が assignee 通知を push する。0 トークン、即時。本人は `assignee:@me label:needs-approval` で承認待ちを一覧できる。

### 7.2 `APPROVED:` コメントで再開する（F5）
- 毎 poll で `--label needs-approval` の open issue も読む。bridge の `NEEDS-APPROVAL:` コメントより後の top-level コメントのうち、`BRIDGE_APPROVERS` の login が書いた `APPROVED:` で始まるものを承認とみなす。
- 再開時は `needs-approval` label を外し、契約ヘッダに `approved: <APPROVED: の本文>` を足して `run_task` を呼ぶ。`harness.PREAMBLE` に「`approved:` にある操作だけ、一度だけ実行してよい」を追記する。
- 承認者は `BRIDGE_APPROVERS`（本人の GitHub login だけ。未設定なら再開機能は無効）で判定する。senders とは別にする。
- 弱点: Grok と Duet の connector は本人 account で投稿するので、Bot が `APPROVED:` を書けば bridge は本人と区別できない。対策は二段。今すぐ: 説明欄と skill で Bot に `APPROVED:` を禁止し、本人は GitHub Mobile から書く。恒久: Bot の connector を別 GitHub account（例 `maylac-bot`）に付け替え、`BRIDGE_ALLOWED_SENDERS` にはその account、`BRIDGE_APPROVERS` には本人だけを入れる。これで login が人と Bot の境界になる。

### 7.3 scope 重複を拒否する（原則 3）
- 契約本文の `Owned files:` 行を読み、`repo + path` を `$HOME/.local/state/slack-bridge/inflight.json` に実行中の間だけ記録する。
- 重なる契約が来たら実行せず、`blocked (duplicate scope #N)` をコメントして close する。Dispatcher は #N の完了後に再起票する。
- `Owned files` が無い契約は実行前に `failed (no owned files)` で返す。契約の品質も上がる。

### 7.4 mission-hub publisher（F4）
- `slack-bridge/publish_hub.sh`: `mission_hub.py --format markdown` の出力に `docs/grok-bot/ops-hub-header.md`（手書きの「本人の判断待ち」「管理範囲」）を前置し、`gh issue edit 6 --body-file` で更新する。
- launchd `com.maylac.mission-hub-publish`: `StartInterval 1800`。07:30 JST の回だけ `gh issue comment 6 --body-file`（先頭 20 行）も行い、メールを発生させる（5.3）。
- session-triage の `latest.md` があれば末尾に「Claude iOS セッションの要確認」として連結する。スマホから見る一覧が一枚になる。

### 7.5 Remote Control host の整理（F7）
| host | 設定 | 用途 |
|---|---|---|
| `workspace` | `--spawn=same-dir --capacity 4`、cwd `$HOME/workspace` | 設計・調査・多 repo。実装はしない（同一 dir で隔離が無い） |
| `vantik` | `--spawn=worktree --capacity 3`、cwd `$HOME/workspace/maylac/reskilling-os-rc` | Vantik の実装。`reskilling-os-rc` を `~/.claude.json` の `projects` に `hasTrustDialogAccepted: true` で登録して起動失敗を直す |
| `agents-setup` | `--spawn=worktree --capacity 4` | `StandardOutPath` を `/dev/null` にして `stdout.log` 363 MB を消す。再起動が要るので 9 の承認項目 |

- 規則: 「どの入口でも、実装は worktree の host で」。`workspace` host で始めた作業がコードに及ぶときは、契約を起票するか `vantik` / `agents-setup` host で開き直す。

### 7.6 doctor に健康診断を足す
- `gh auth status` の成否、`launchctl print` の各 Remote Control host の state、`stdout.log` の size、`inflight.json` の古さ（1 時間超は警告）。
- publisher がこの結果を issue 6 の末尾に「Mac の状態」として載せる。本人は「状況」Skill だけで Mac の健康を知れる。

## 8. 段階計画と受け入れ確認

### Phase 0（今日から、承認不要）
1. この文書を PR にする。
2. 7.1〜7.3 を bridge に実装し、fake executable のテストを足す。
3. 7.4 の `publish_hub.sh` と plist template を追加する（install は Phase 1）。
4. `dispatcher-instructions.md` と `bot-roles.md` を 4.1・4.2 の内容に改訂する。
5. `skills/phone-dispatcher/SKILL.md` を `dispatcher-instructions.md` から生成する。

確認:
```sh
python3 -m unittest discover -s slack-bridge -p 'test_*.py'   # 既存 44 + 追加分が pass
python3 slack-bridge/doctor.py --check-github                 # github_repo が present
git diff --check
```

### Phase 1（本人の判断が要る）
1. `com.maylac.mission-hub-publish` を bootstrap する。
2. bridge の env に `BRIDGE_APPROVAL_ASSIGNEE`、`BRIDGE_APPROVERS`、`reskilling-os` を足し、idle のときに 1 回だけ再起動する。
3. `agents-setup` host の plist を `/dev/null` 化して再起動する（2 と同じ保守時間で）。
4. `reskilling-os-rc` の trust を登録し、`vantik` host を再起動する。
5. GitHub Mobile を入れ、assignee 通知を on にする（スマホ操作のみ）。承認はここから `APPROVED:` をコメントする。

確認:
```sh
launchctl print "gui/$(id -u)/com.maylac.mission-hub-publish" | grep state
gh issue view 6 -R maylac/agent-tasks --json updatedAt --jq .updatedAt   # 35 分以内
python3 slack-bridge/doctor.py                                            # RC host 3 本が running
```
smoke: `NEEDS-APPROVAL:` を出す契約を 1 本流す → GitHub Mobile に push が届く → `APPROVED: <操作>` をコメント → bridge が再開して `done`。

### Phase 2（Duet）
1. waitlist と US account の条件を本人が判断する。
2. Gmail と Slack を Duet に接続する。
3. `phone-dispatcher` skill を Claude account に入れる。
4. 朝ブリーフに 07:30 のコメントが載ることを 2 日続けて確認する。
5. 検品 1 本（`VERIFIED:` を Duet が下書き、本人が送信承認）。

### Phase 3（Muse、任意）
1. Muse を使える条件を本人が判断する。
2. Slack `#inbox` を作り、Muse を接続する。
3. Grok の 08:00 routine に「`#inbox` を読む」を足す。

## 9. 本人の判断が必要な項目

- bridge の再起動（env 変更と `reskilling-os` 追加）。実行中の agent を殺すので、idle のとき 1 回だけ。
- `agents-setup` host と `vantik` host の再起動（plist と trust の変更）。
- 新 LaunchAgent `com.maylac.mission-hub-publish` の登録。
- Duet の waitlist 登録と、Gmail / Slack の OAuth 接続。
- Muse の利用可否と Slack `#inbox` の接続。
- Grok の追加 3 Bot を作らない決定（規約同意をしない）。
- Bot の GitHub connector を別 account（例 `maylac-bot`）に分けるか。分ければ Grok / Duet 経由の承認返答を login で区別して許可できる。分けないなら承認は GitHub Mobile からだけ。
- 課金・プラン・自動チャージは一切変えない。

## 10. 参考

- Claude Duet: [Get started with Claude Duet](https://support.claude.com/en/articles/17631495-get-started-with-claude-duet)、[Introducing Claude Duet](https://claude.com/resources/articles/claude-duet)（2026-11-01 閲覧。接続先の一覧に GitHub と Claude Code は無い。利用枠はプランと共有）
- Muse: [Meta introduces Muse](https://www.therundown.ai/news/meta-muse-personal-ai-agent)、[Meta Muse Connectors list](https://postfa.st/blog/meta-muse-connectors-list)（二次情報。公式の connector 一覧は未公開）
- Grok Bot: `docs/grok-bot/README.md`、`bot-roles.md`、`dispatcher-instructions.md`、`activation-plan.md`
- 監査: `docs/harness-audit-2026-10-13.md`（A7・A9・A10・E が未対応のまま）
- bridge: `slack-bridge/bridge.py`（`classify_output`、`poll_github_once`、`github_tasks`、`parse_contract`）、`harness.py`（`PREAMBLE`、routing）、`mission_hub.py`
