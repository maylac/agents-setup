# Public Safety Policy

This repo is public-safe by construction, not by trust.

Included:

- reusable skill source and documentation
- public-safe home and tool instruction files
- custom hooks and commands after path/token redaction
- plugin IDs and restore commands
- public settings templates

Excluded:

- API keys, tokens, cookies, sessions, and auth files
- local databases, message stores, logs, telemetry, caches, and histories
- generated plugin caches and downloaded marketplace payloads
- full `~/.codex/config.toml` and `~/.claude/settings.local.json`
- nested upstream repos that should be restored from their origin

Before publishing, always run:

```sh
scripts/validate.sh
```

If validation flags a false positive, prefer adding a narrower sanitizer or an
exclusion note over weakening the scan globally.
