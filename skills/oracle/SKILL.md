---
name: oracle
description: Consult a stronger second model with bundled file context for hard diagnosis, architecture review, or stuck problems.
origin: steipete/oracle
---

# Oracle — one-shot consult of a stronger model with file context

Oracle bundles a prompt **plus the actual source files** and sends them to a
heavyweight model (default `gpt-5.5-pro`) for a single, deep answer. Reach for it
when you are stuck, need a second opinion, or face a problem that benefits from
large file context and server-side reasoning — root-cause hunts, cross-repo
comparisons, architecture/security review, "why is this subtly wrong" questions.

CLI: `oracle` (pinned to Node 24 via `~/.local/bin/oracle`). Install lives at
`/opt/homebrew/lib/node_modules/@steipete/oracle`.

## The one rule that matters

**Always pass BOTH a prompt AND `--file`.** Oracle starts empty and cannot see
the project otherwise. Attach generously — whole directories and globs beat
single files — and keep total input under **~196k tokens**.

```bash
oracle -p "<6–30 sentence briefing + the actual question + what you already tried>" \
  --file "src/**/*.ts" --file "!src/**/*.test.ts"
```

Open with a short project briefing (stack, services, build steps), spell out the
question and prior attempts, and say why it matters. Very short prompts yield
generic answers. When comparing files/repos, label each one (repo + path + role)
so the model knows what it is reading.

## Authentication / engine

`-e, --engine <api|browser>`. If omitted, Oracle picks **api** when
`OPENAI_API_KEY` is set, otherwise **browser**.

- **browser** — automates a signed-in ChatGPT (GPT models) / cookie-based
  gemini.google.com (Gemini). No API key, no metered cost. Good default for
  interactive use.
- **api** — uses `OPENAI_API_KEY` (or Azure flags). **This costs money.** Only
  trigger an API run when you explicitly mean to, and get the user's consent
  first. Never set the key yourself — the user must provide it.

Force one explicitly with `--engine browser` or `--engine api`.

## Token budget — check before you spend

`--files-report` prints per-file token usage (also auto-prints when files exceed
the budget). `--dry-run` (summary|json|full) previews the bundle without calling
the model. `--render` prints the assembled markdown; `--copy-markdown` puts it on
the clipboard for manual paste.

## Sessions — never blindly re-run

Non-preview runs (especially `gpt-5.5-pro` API) spawn **detached** sessions and
can take a long time. If the CLI times out, **do not re-run** — reattach:

```bash
oracle status                 # recent sessions (24h window; --hours, --all)
oracle session <id|slug>      # attach and stream the saved transcript
```

A duplicate-prompt guard blocks an identical prompt that is already running
unless you pass `--force`; prefer reattaching. Give a tidy `--slug "3-5 words"`.

## Useful flags

- `-m, --model <name>` — e.g. `gpt-5.5-pro` (default), `gpt-5.5`, `gpt-5.4-pro`,
  `gpt-5.4`, `gemini-3-pro`, `claude-4.5-sonnet`.
  **GPT-5.6 (sol/terra/luna, 2026-07-09 GA) は oracle 0.15.2 時点で未対応** —
  未知のモデル名はエラーにならずフォールバックする(browser モードでは
  `gpt-5.2` に落ちる)ので、CLI が対応するまで 5.6 系の名前を渡さないこと。

## モデル選択の運用ルール (2026-07-12 決定)

- 許可モデルは上記 `-m` の列挙リストのみ。リスト外の名前は渡さない
  (サイレントフォールバック防止)。既定 `gpt-5.5-pro` 据え置きは、npm 最新
  (0.15.2) が 5.6 系未対応であることを確認した上での明示的決定。
  新版が 5.6 対応したら既定を `gpt-5.6-sol` 系へ更新すること
  (`npm view @steipete/oracle version` で確認)。
- **セカンドオピニオンの経路分担**: Google 視点は `-m gemini-3-pro`、
  Claude 視点は oracle ではなく `fable-escalation` スキル経由の Fable を正とする
  (`claude-4.5-sonnet` は旧世代のため oracle 経由では使わない)。
- `--models a,b` — query several API models in parallel and aggregate.
- `--followup <sessionId|responseId>` — chain a follow-up (API runs).
- `--write-output <path>` — write only the final assistant message to a file.
- `--timeout <s|auto>` — auto = 60m for Pro models, 120s otherwise.

## Safety

- **Do not attach secrets** (`.env`, keys, tokens, credentials) — file contents
  are sent to a third-party model. Exclude them with `--file "!**/.env*"`.
- Treat API runs as a metered, consent-gated action.

## Examples

```bash
# Browser run (no API key), TS data layer minus tests
oracle --engine browser -p "Review the TS data layer for schema drift; we suspect the Zod schema and the DB row type have diverged. Stack: Node 24 + Drizzle. What I tried: ..." \
  --file "src/**/*.ts" --file "!src/**/*.test.ts"

# Cross-repo comparison — label each file's role
oracle -p "Tabs freeze on switch. Compare App A SettingsView vs App B SettingsView and find the divergence." \
  --file appA/Sources/SettingsView.swift \
  --file ../appB/mac/App/Presentation/Views/SettingsView.swift

# Inspect token spend first, then decide
oracle --files-report -p "Summarize risk register" --file docs/

# Reattach instead of re-running after a timeout
oracle status
oracle session release-readiness-audit
```
