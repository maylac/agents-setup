# Claudeのモデル認証なしでユーザーskill登録を検証する

- 日付: 2026-07-10
- 領域: agents-setup / Claude Code skill migration
- 種別: debugging

## 問題

旧 `~/.claude/commands` から `~/.claude/skills` へ移行した後、新規Claudeプロセスがskillを登録することを確認したかった。しかし、モデル応答を使う `claude -p` は非対話環境の未認証状態で停止する。

## 試して駄目だった道

- `claude --bare -p` で利用可能なskill名を回答させようとしたが、`Not logged in` で停止した。
- `--bare` のデバッグログは reduced mode となり、ユーザーskillディレクトリの探索自体をスキップした。

## 効いたアプローチ

1. `--bare` を外し、`--debug-file` 付きで通常モードのClaudeを起動する。
2. モデル応答の成否と切り離し、デバッグログの `Loading skills from` と `getSkills returning` を検査する。
3. 正本ストアからClaude除外パターンを差し引いた期待件数を独立計算し、ローダーの登録件数と照合する。
4. 必須skillは個別にsymlink先、`SKILL.md` 存在、frontmatterの `name == directory` を検証する。

## なぜ効いたか

Claude Codeはモデルへの認証・応答より前にローカルskillディレクトリを初期化する。通常モードのデバッグログはそのローダー結果をモデル認証と独立に示す。期待件数と個別frontmatterを別系統で検証することで、単にログが出ただけでなく移行対象の登録を確認できる。

## 一般化できる原則

モデル認証が使えないCLI設定検証では、モデル応答を完了条件にしない。認証前に実行されるローカル初期化ログと、独立計算した期待状態の両方を照合する。

## 2026-10-15 follow-up: runtime discovery boundaries

- Claudeのfresh-process `stream-json` `system/init` は、`Read` と `Skill` toolsが有効な状態で `yomiyasu` を列挙した。`--tools ''` による先行probeはskill一覧が空だったが、tool discoveryを無効にした条件の結果であり、インストール失敗を示すものではなかった。
- Codexの `skills/list` `forceReload` は、正本の `$HOME/workspace/maylac/agents-setup/skills/yomiyasu/SKILL.md` を `enabled: true` として返した。上流package metadataにより名前は `yomiyasu:yomiyasu` となるため、単純名 `yomiyasu` だけの一致確認はfalse negativeになる。返却名に加えて正本pathとenabled状態を確認する。
- Antigravityはglobal skill pathを検出したが、`view_file` による正本の読み取りは現在のpath permissionで拒否された。配置済みであることは確認できたが、利用可能とは判定しない。限定した `read_file` ルールへの明示承認が得られるまでblockedとして扱い、提案JSONだけでpermissionを変更しない。
- 実行証拠: `$HOME/tasks/yomiyasu-install-20261015/claude-discovery.json`、`codex-discovery.json`、`agy-settings-proposed.json`。

- Resolution on 2026-10-15: after explicit user approval for the single `read_file` rule on the canonical skill directory, Antigravity's `view_file` succeeded through `$HOME/.gemini/config/skills/yomiyasu/SKILL.md`. Its final response confirmed both `意味の保持` and `情報の不増補`; the stream had a successful tool step, a non-empty final response, and no `denied_actions`. The earlier denial remains the historical pre-approval result. The settings file was absent before approval and was created with only the approved rule.
