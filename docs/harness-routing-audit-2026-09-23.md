# ハーネスのAstra/Lunaルーティング監査

- 証跡日: 2026-09-23
- 対象: `~/workspace/maylac/agents-setup` と live `~/.codex/config.toml` / `~/.codex/agents/*.toml`。Codex CLI `0.155.0-alpha.9.2`。

## 配置

Codexの27 custom agentsはAstra 14 / Luna 13。Astraはplanner、architect、11 reviewer、loop-operator（監督・停滞介入）。残る実装・修正・docs・E2E・loop以外の実行役とchief-of-staffはLuna。親はAstra / xhighを維持し、child defaultはLuna / high。個別agent effortキーは公式schemaに合わせ `model_reasoning_effort` とし、既存levelを保った。

skillsの正本はrepo内 `skills/`。実機では `~/.agents/skills/<name>` がrepoへのsymlinkで、Codexの `~/.codex/skills/<name>` はさらに `~/.agents/skills/<name>` を参照する。`scripts/sync-skills.local.sh` がlive mirrorを扱う。ClaudeのFable settings templateと `fable-advisor` / `fable-verifier` は明示指定時だけ使うClaude互換経路として保持。

27 agent TOMLはrepo/live間でSHA-256一致。`scripts/backup.sh` のCodex template生成ブロックとpublic templateも一致し、生成元に新しい親・child既定がある。親Astraが別途 `scripts/sync-instructions.sh --check` と `git diff --check` を通過確認した。既存のdirty skill変更は保持し、backup.sh全体は実行していない。

## 検証と制約

指定6テスト（backup-sanitize、audit-sync-fixture、install-behavior、sync-skills-local、validate-rules-frontmatter、rtk-rewrite-hook）は全てPASS。`scripts/validate.sh` 全体はFAIL: live `~/.claude/settings.json` と `~/.codex/hooks.json` が無く、JSON検査も失敗。現環境に `~/.hermes` とHermes CLIもなく、この経路は未導入として扱う。repo内のCodex hooks snapshot、Claude settings templateは存在する。

`codex exec --strict-config --ephemeral --skip-git-repo-check --sandbox read-only -m gpt-6-luna "Reply with only OK."` は終了0で `OK`。これは明示モデルLunaのsmokeとconfig読込確認であり、親のdefault解決証拠ではない。Astra親からoverrideなしのgeneric child spawnは2回試した。ephemeral runは `collab spawn failed: no thread with id`。通常session retryはCLI終了0だったが、JSONLは `wait` eventのみで `receiver_thread_ids` は空、spawn eventも子threadもなかった。子の実モデルを示す機械的証拠は得られず、default spawnは未検証。

既存の別スレッドで明示指定されたモデルを一括変更したものではない。保存設定は新しい起動・子起動から適用され、既存セッションは必要に応じて設定を読み直す。既存のdirty skill変更はそのまま保持した。

モデル設定と `model_reasoning_effort`、`[agents]` の `default_subagent_model` / `default_subagent_reasoning_effort` は[公式Subagents docs](https://learn.chatgpt.com/docs/agent-configuration/subagents)に準拠。
