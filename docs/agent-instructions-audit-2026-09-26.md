# エージェント指示ファイル監査 — 2026-09-26

## 対象と方法

共通指示の正本、Claude/Codex向けの関連ルールと生成ファイル、repo rootの `AGENTS.md`、workspace内の自作プロジェクト指示ファイルを確認しました。第三者配布物、依存パッケージ、プラグインcache、アプリ内プロンプトは対象外です。第三者の生成コピーは除外し、実行時に使う自前の `claude/CLAUDE.md` は確認対象に含めています。

- 正本と関連資料: `home/AGENTS.md`、`home/claude-header.md`、`home/soul-core.md`、`claude/AGENTS.md`、`claude/DESIGN.md`、`claude/RTK.md`、`claude/rules/common/agents.md`、`claude/rules/common/performance.md`、`scripts/sync-instructions.sh`。`~/CLAUDE.md` は `~/AGENTS.md` への互換symlinkです。
- `claude/CLAUDE.md` は `home/claude-header.md` から生成されるファイルです。repo rootの `AGENTS.md` はhome指示とは別のrepo案内として維持しました。project内の11件の `CLAUDE.md` symlinkは既存の正本へのaliasです。
- プロジェクト指示は13件の正本を確認済み。`--no-ignore` とリンクを識別する走査でも追加はなく、既存対象を指す11件の `CLAUDE.md` aliasと8件のdirectory symlinkも確認しました。リンク構成は変更していません。
- 外部根拠は2026-09-26に確認した公式資料です。Claudeアプリはv2.9939.2、Claude Code CLIはPATH上で見つからず、CLIの稼働版と挙動は未確認です。現行Claude docsでは直接の `AGENTS.md` 読み込みはv2.1.277以降です。

## 共通指示と関連ルール

| ファイル / 見出し | 判定 | 確認結果と反映内容 |
|---|---|---|
| `AGENTS.md` — Agent Guide | Keep | このrepoの目的、構成、検証スクリプト、symlink保全を案内する独立したrepo指示です。変更なし。 |
| `home/AGENTS.md` — Core Principles 1 | Update済み | 「不明なら停止して質問」を、重要な曖昧さだけ尋ね、通常は前提を示して進める表現に更新しました。同じファイル内の音声入力ルールとの矛盾が解消されています。 |
| `home/AGENTS.md` — Tool Use Rules | Update済み | `ax` をPATH上で確認できる場合に優先し、なければ利用可能なブラウザ/Web手段を使うよう変更。X用 `opencli` も、実行ファイルと対応コマンドを確認できる場合に限定しました。 |
| `home/AGENTS.md` — RTK / Graphify | Update済み | `rtk` / `graphify` が使える条件を明記。RTKのhook登録確認を加え、測定時の詳しい注意を `claude/RTK.md` に移しました。Graphifyは対象repoにgraphがある場合の補助として扱い、通常検索の代用にしないよう変更しました。workspace内25 repoにgraph出力がなく、「全repoにgraphがある」という記述は誤りでした。 |
| `home/AGENTS.md` — Cross-Harness Model Routing | Keep | Astra/Lunaの役割とモデル選択はCodexおよび明示的にCodexへ委譲した作業に適用します。Claudeのnative routing exceptionは別途記載しています。 |
| `home/AGENTS.md` — Plan Infographic Approval Gate | Keep・Update済み | 計画承認後、実装前にskillを実行し、成果物のユーザー承認まで編集しないゲートを維持。`ExitPlanMode` / `AskUserQuestion` は利用中の環境が提供する場合だけ使い、無応答を承認と扱わない表現にしました。 |
| `home/AGENTS.md` — Local Tools | Update済み | まずコマンドの有無と対応optionを確認するよう変更。存在を確認できないツールやsimulatorを前提にしません。 |
| `home/claude-header.md` — Workflow / Plan / Design | Update済み | Claudeのhome指示は `~/CLAUDE.md` symlink経由と明記。Claude固有のproject `AGENTS.md` 読み込みを無条件に断定せず、読み込み済み指示の確認と、repo `AGENTS.md` を明示的に読む手順を記載しました。`/context` は確認時に使えるCLI例です。Planは曖昧さ、設計判断、編集前確認が要る場合に使い、通常の複数手順は短い計画を示して続行。Designファイルは有効なsymlinkから探し、利用できるtask別skillも確認します。 |
| `home/claude-header.md` — Model Routing / Codex Collaboration | 一部Update済み | Astra/Lunaへのrouting方針は既存の指示として維持しました。今回の変更は、Codexのnative delegationを現在のsessionで利用できる場合に限る表現です。 |
| `home/claude-header.md` — Mobile Completion Reporting | Update済み | `~/.agents/hooks/notify-mobile.sh` は指定先に存在しません。通知hookと対象scriptが両方有効な場合だけ通知を前提とし、成功の証拠なしに配信済みとしない表現へ更新しました。 |
| `home/soul-core.md` | Update済み | 不正確なworkspace内絶対pathを `~/AGENTS.md` に変更しました。Astra/Luna routingの記述は既存内容を維持しました。 |
| `claude/AGENTS.md` — Local Map | Update済み | repo内 `skills/` が正本、`~/.agents/skills` はruntime mirrorと記載しました。`~/AGENTS.md` はrepo rootの `AGENTS.md` とは別ファイルです。 |
| `claude/RTK.md` — Historical caveats | Update済み | 長いRTK測定例をここへ移し、2026-07-28時点の観測で、現在のCLIやhookの有効性を保証しないと明記しました。 |
| `claude/rules/common/agents.md` | Keep | 既存のClaude agent案内を読み合わせましたが、今回の監査では変更していません。 |
| `claude/rules/common/performance.md` | Update済み | Plan Modeの固定「3+ step」基準を外し、判断が要る計画と短い計画で進められる通常作業を区別しました。 |
| `claude/DESIGN.md` — delegation map | Update済み | 現環境のskill/plugin一覧にない `dataviz`、`artifact-design`、`frontend-design` を利用可能な可視化、hallmark、presentation skillへ置換しました。 |
| `scripts/sync-instructions.sh` | Keep | 既存の生成・同期scriptを利用しました。今回の監査では変更していません。 |

**Claudeの指示読み込み:** 現行公式資料によると、祖先に `CLAUDE.md` がある場合、既定ではproject `AGENTS.md` は読み込まれないことがあります。両方読む設定はこの監査では変更していません。Claude Code CLIが確認できないため、実行時には `/context` を確認し、repo指示が見えなければ対象 `AGENTS.md` を読むよう案内しています。

## プロジェクト指示ファイル (正本13件)

| ファイル | 判定 | 根拠と反映内容 |
|---|---|---|
| `maylac/polymarket-signal-agent/AGENTS.md` | Keep | Python CLI、tests、docs、dataのpathと用途が一致。 |
| `maylac/myLife/CLAUDE.md` | Keep | 参照schema、skills、入口の説明が一致。既存のuntracked raw noteは対象外・未変更。 |
| `maylac/image_renamer/AGENTS.md` | Keep | Python scripts、Docker入口、test suiteとコマンドが一致。 |
| `maylac/mf-dashboard/AGENTS.md` | Update済み | 存在しない `src/crawler/` とcrawler固有guardrailを削除。現存する `src/lib/` をdata helpersと記載。 |
| `maylac/ai-executive-pipeline/AGENTS.md` | Keep | npm scriptsとapp/lib/tests/public構成が一致。 |
| `maylac/reskilling-os/AGENTS.md` | Update済み | 存在しない `frontend/` を削除し、UIの実path `src/` を記載。NAS deploymentの要求は既存のユーザー方針で、古くなった証拠がないため維持。 |
| `maylac/solo-job-ledger-android/AGENTS.md` | Keep | Gradle path/commandsとrelease signingの条件が一致。 |
| `maylac/agent-notch/AGENTS.md` | Keep | SwiftPM check target、Backlog手順、ローカル安全境界を確認。 |
| `maylac/asset-lakehouse/AGENTS.md` | Keep | npm/TypeScript/Backlog commandとsource/data構成が一致。 |
| `maylac/nas-media-viewer/AGENTS.md` | Keep | compose、backend requirements、frontend package scripts、directory構成が一致。 |
| `maylac/heygen-codex-video-studio/AGENTS.md` | Keep | HyperFrames composition構成とrender/uploadの安全境界が一致。 |
| `maylac/FolioCapture/AGENTS.md` | Update済み | `swift run FolioCaptureChecks` はSwiftPM check executableと明記。XCTestとの差はREADMEへ案内。 |
| `maylac/hermes-satellite/AGENTS.md` | Keep | CLI entrypointとtest pathを確認。既存変更済み `pyproject.toml` は未変更。 |

## 実施内容と検証状況

- Lunaが公式資料、実行環境、指示pathとCLI inventoryを調査し、上表のglobal/project指示変更と10項目の個別確認を実行しました。Astraは `reskilling-os` のdeployment文言を変更する提案を却下しました。既存のユーザー方針で、陳腐化の根拠がなかったため維持しました。
- agents-setupの既存ファイル8件（`claude/CLAUDE.md` の生成物を含む）と、プロジェクトの `AGENTS.md` 3件を更新し、監査報告と解決手順の学習記録2件を追加しました: [共有指示の発見方法](learnings/2026-09-26-shared-instruction-discovery.md)。
- Project確認: `mf-dashboard` のdata helperあり/crawlerなし、`reskilling-os` の `src/` あり/`frontend/` なし、npm scripts、FolioCapture executable targetを確認。10項目の個別確認と3ファイルの `git diff --check` はpass。project build/test suiteは実行していません。
- 最終確認: `bash scripts/sync-instructions.sh --check` はexit 0。生成ファイルと正本の内容一致、および9件のsymlink先を確認しました。対象8ファイルの `git diff --check` もexit 0です。
- `bash scripts/validate.sh` は編集後の主要変更時点でexit 1となり、編集前と同一の失敗ログでした。原因は現在の環境で `~/.claude/settings.json` と `~/.codex/hooks.json` が見つからず、validatorがruntime設定を読み込めないことです。最後のheader表現修正後は全体validatorを再実行せず、上記のsync、生成物parity、symlink、diff確認を行いました。実行設定は作成していません。
- `scripts/audit-sync.sh` はCodex hooks欠落で途中停止。停止前の11 symlink checksとRTK hook-pair checksはpassしましたが、全mirror parityは未検証です。
- `hermes-satellite/pyproject.toml` の既存差分と `myLife` のraw noteは変更していません。
- 現環境で `command -v` が見つけなかったもの: `ax`, `opencli`, `rtk`, `graphify`, `omniget`, `backlog`, `claude`, `maestro`。これはPATH上で見つからないという結果で、Claudeアプリのように別の場所で確認したものを除き、全インストール先を調べた意味ではありません。`~/.agents/hooks/notify-mobile.sh` と `.claude` / `.codex` のlive settingsも確認できませんでした。

## 公式資料 (2026-09-26確認)

- OpenAI, [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra), 2026-09-11: 古い強い境界指示がAstraの停止を早める場合があるため、指示とskill記述を現行モデル向けに見直すよう説明。
- OpenAI, [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[Developer commands](https://learn.chatgpt.com/docs/developer-commands)、[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): 常時指示を短く実用的に保つこと、Codex `/plan` とsurface別のdelegation/model設定。
- Anthropic, [Claude Code memory](https://code.claude.com/docs/en/memory)、[settings](https://code.claude.com/docs/en/settings)、[permissions](https://code.claude.com/docs/en/permissions): `AGENTS.md`対応version、祖先 `CLAUDE.md` の優先、指示と強制設定の違い。
- Anthropic, [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)、[hooks](https://code.claude.com/docs/en/hooks)、[skills](https://code.claude.com/docs/en/skills): subagentのtool/model制限、hookの実行条件、skillの読み込みとcontext負荷。
