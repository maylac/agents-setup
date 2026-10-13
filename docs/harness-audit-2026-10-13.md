# ハーネス運用監査 — 2026-10-13

対象: Slack / iPhone から Mac mini 上の Claude Code・Codex・Antigravity を動かす運用。調査ソースは `agents-setup` の main 作業ツリー(実機の正本)と HEAD の差、`~/.claude` `~/.codex` の実設定、launchd、Remote Control ログ、Claude Code Remote のセッション一覧(コスト・コンテキスト)、Slack の Dots DM 履歴(10/10〜10/13)、`docs/learnings`・`~/tasks`・auto-memory。

## A. バッドプラクティス(事故・損失につながる)

| # | 事象 | 証拠 | 対応 |
|---|---|---|---|
| A1 | 正本リポジトリが 2 か月分コミットされていない(151 件の未コミット差分、HEAD は 2026-08-17)。Remote Control の worktree は古い HEAD から切られるため、モバイル起動のセッションは毎回古い指示を読む | `git status`、HEAD と live の `home/AGENTS.md` の md5 不一致 | PR `snapshot/harness-drift-2026-10` で作業ツリーをそのままスナップショット |
| A2 | Codex が `sandbox_mode = "danger-full-access"` + `approval_policy = "never"` + `model_reasoning_effort = "ultra"`。2026-07-17 にユーザーが却下した構成が復活している | `~/.codex/config.toml`、`docs/learnings/2026-07-17-*` | 承認待ち(§E) |
| A3 | 指示ファイルが未導入ツールを前提(`ax` `opencli` `rtk` `graphify` `paseo` `hermes` `backlog` `omniget` `maestro` `tmux`、`~/.agents/hooks/notify-mobile.sh`) | `command -v` 全滅、`~/.hermes` `~/.paseo` 不在 | `home/AGENTS.md` の Tool Use Rules を「`command -v` で確認してから使う」1 条に集約 |
| A4 | hooks が 1 つも登録されていない(`~/.claude/hooks/` に 6 本、`settings.json` に `hooks` なし、`~/.codex/hooks.json` 不在)。唯一のプロジェクト hook は旧パスで no-op | `settings.json`、`claude/hooks/post-write-check.sh` | hook のパスを修正(PR2)。通知は Claude Code 内蔵 push と Dispatcher の Slack 投稿に寄せる |
| A5 | `~/.local/bin/codex` symlink が 9/27 から壊れたまま | memory `codex-cli-path.md` | 実機で `codex-cli/bin/codex` に張り替え済み(`codex --version` = 0.162.0-alpha.17.2) |
| A6 | Dots とユーザーが同じ Claude に二重指示 → 二重編集回避で Dots が停止 | Slack DM 10/12 04:10〜04:52 | 指示経路を Dispatcher → GitHub Issue → bridge に一本化(`home/AGENTS.md` Single command path) |
| A7 | Claude Pro の 5 時間制限(429)で実装が止まり、Dots が「未ログイン」と誤診断 | Slack DM 10/11 03:38〜04:11 | bridge が 429 を Issue に書き、Codex(`gpt-6-luna`)へフォールバック |
| A8 | GitHub Actions 無料枠 2,000 分を消費し、CI を NAS self-hosted runner へ退避 | Slack DM 10/12 21:43 | flaky な mobile-webkit E2E を quarantine し必須チェックから外す(Vantik 側の課題) |
| A9 | Remote Control の容量 4/4 が常時埋まり、idle の Vantik セッション 3 本が slot と locked worktree を占有 | `stdout.log`、`list_sessions` | archive は承認待ち(§E)。archived セッションの worktree 2 本は削除済み |
| A10 | `~/.claude/remote-control/stdout.log` が 108 MB・ローテーションなし | `du` | launchd の `StandardOutPath` を `/dev/null` へ(§E、永続化変更のため未実施) |
| A11 | スクリプト・launchd テンプレ・skill が旧パス `$HOME/workspace/agents-setup` を参照。`sync-instructions.sh` は drift 内で修正済みだったが残り 7 箇所が未修正で、週次 rot 監査は一度も動いていない | `rg 'workspace/agents-setup'`、`selfimprove/reports/` 空 | PR2 で修正 |
| A12 | `validate.sh` の秘匿パス検出が `gotasa\+ki`(rg では literal `+`)で `/Users/<user>` を検出できない | `scripts/validate.sh:129` | PR2 で修正 + 回帰テスト追加 |

## B. 非効率(トークン・時間・金)

| # | 事象 | 証拠 | 改善 |
|---|---|---|---|
| B1 | 1 セッションを巨大化させる運用。Vantik セッションがコンテキスト 403k〜676k、cache_read 84M〜180M、$32〜$58/セッション | `list_sessions` usage | 1 タスク = 1 セッション。bridge の worktree 使い捨てで強制 |
| B2 | 「枠がリセットされるから」と Codex を 20 分ヒートビートで走らせ、途中で枠切れ・下書き散乱 | `~/tasks/codex-usage-20261013/CONTROL.md` | 枠消化を目的にしない。残枠は bridge キューへ |
| B3 | モデルルーティングの記述が 6 か所、HEAD と live で内容が異なる | `AGENTS.md` `CLAUDE.md` `performance.md` `agents.md` `soul-core.md` `consult.py` | `home/AGENTS.md` の 1 節に統合(PR3) |
| B4 | 「Claude が実装を担う」(Dots 節)と「既定で Codex に分割」(Cross-Harness 節)が同一ファイルで矛盾 | `home/AGENTS.md` | ディスパッチ run は分割しない、対話セッションのみ分割、と明記 |
| B5 | Dots が小さな判断ごとに承認を求め、ユーザーが「反応しろ」「無理くり続けさせろ」と催促 | Slack DM 10/10〜10/12 | 契約に権限を書き、Hard Stop 以外は聞かない(Dispatcher 指示文) |
| B6 | Dots が Mac の Chrome で Claude Web を画面スクレイプして状況確認 | Slack DM 10/12 04:43 | 状態は Issue / PR / CI に置く |
| B7 | flaky な mobile-webkit E2E を CI でそのまま再実行(10/13 も 20 件失敗) | handoff | quarantine |
| B8 | skills 95 本(7 月に 82 まで削減後に再増殖)、多くが CLI 未導入 | audit | 未導入 CLI 依存 skill は description 冒頭に要件を明記 |
| B9 | worktree 8 本(うち locked 5) | `git worktree list` | archived 2 本を削除済み。残りは §E |
| B10 | Codex automations 3 本が PAUSED のまま、`vantik` は UNTIL 期限切れ | `~/.codex/automations` | 不要なら削除(ユーザー判断) |

## C. QOL・価値向上

1. 司令塔を Grok Bot に一本化し、Mac mini への経路を GitHub Issue bridge に統一(`docs/grok-bot/README.md`)。
2. Remote Control を 2 系統(agents-setup / reskilling-os)にして iPhone から Vantik 作業を直接開く(§E)。
3. 指示ファイルを実機にあるものだけに刈り込む(PR3)。
4. Claude 429 時は bridge が reset 時刻を書き、Codex へフォールバック。
5. Grok Bot のルーティンで毎朝 08:00 JST に open issues / PR / CI 失敗 / NAS 疎通を Slack へ要約。
6. パス修正後に `self-improve` の週次 rot を launchd で稼働(§E)。
7. 通知は Claude Code 内蔵 push(`agentPushNotifEnabled`)と Dispatcher の Slack 投稿へ寄せ、死んだ `notify-mobile.sh` 系の記述を削除。

## D. 実施済み(2026-10-13)

- ブランチ `snapshot/harness-drift-2026-10`(main 作業ツリーのスナップショット、2 docs の `$HOME` 化)
- ブランチ `fix/repo-path-and-validate-regex`(旧パス 7 箇所、validate 正規表現、回帰テスト、attribution 記述)
- ブランチ `docs/harness-audit-2026-10`(本書、`home/AGENTS.md` の刈り込み、learnings)
- 実機: `~/.local/bin/codex` 修復、`~/.local/bin/rg` 導入(validate.sh の前提)、archived セッションの worktree 2 本削除(`01Pzf8…` `012EPf…`)、plan を `~/tasks/plan-reviews/2026-10-13-harness-audit-grok-bot.md` に保存

## E. 承認待ち・ユーザー操作が必要

- 4 ブランチは 2026-10-14 に push 済み。`gh pr create` は権限分類で拒否されたため、PR 作成はユーザー操作(`docs/grok-bot/README.md` §5)。
- launchd の変更(永続化)はすべて拒否された: `stdout.log` の `/dev/null` 化、2 系統目の Remote Control(`local.claude.remote-control-vantik.plist`)、週次 rot の `install_launchd.sh`。plist の内容は `launchd/local.claude.remote-control.plist.template` に置いた。
- Codex live 設定: `sandbox_mode = "workspace-write"`、`model_reasoning_effort = "high"`。
- idle な Vantik セッション 3 本(`011hdi…` `018R2V…` `013TSX…`)の archive と worktree 削除。`01SrSn…` は未コミット変更 4 件があるため保留。
- Grok Bot のアカウント操作・OAuth・bridge 起動・Dots 停止。
- Claude プランの見直し(Pro の 5 時間制限が自律運転のボトルネック)。
