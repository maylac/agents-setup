# Restore Notes

Use this repo as a public-safe blueprint, then restore secrets from Keychain,
1Password, environment variables, or provider dashboards.

## Skills

Dry-run:

```sh
scripts/install.sh
```

Apply skill symlinks into `~/.agents/skills`:

```sh
scripts/install.sh --apply
```

Then sync runtime mirrors with the local sync helper if available:

```sh
~/.agents/sync-skills.sh --dry-run
~/.agents/sync-skills.sh
```

## Instruction Files

This repo is the canonical source for public-safe instruction files and scoped
rules. Review the dry-run first:

```sh
scripts/install.sh --instructions-only
```

Apply symlinks from the live home config back to this repo:

```sh
scripts/install.sh --apply-instructions --instructions-only
```

The installer backs up replaced instruction files under
`~/.agents-setup-backups/<timestamp>/`.

Canonical snapshots:

- `home/AGENTS.md`
- `home/CLAUDE.md`
- `claude/CLAUDE.md`
- `claude/AGENTS.md`
- `claude/rules/common`
- `codex/AGENTS.md`

The intended symlink shape is:

```text
~/AGENTS.md -> <repo>/home/AGENTS.md
~/CLAUDE.md -> AGENTS.md
~/.claude/CLAUDE.md -> <repo>/claude/CLAUDE.md
~/.claude/AGENTS.md -> <repo>/claude/AGENTS.md
~/.claude/rules/common -> <repo>/claude/rules/common
~/.codex/AGENTS.md -> ../AGENTS.md
```

The backup sanitizer rewrites local home paths and Claude project-id fragments
such as `-Users-...` when snapshots are generated. If a future snapshot contains
an explicit `[redacted-*]` placeholder, resolve it manually before promoting that
file into a live symlink.

## Claude Code

Review these directories before applying:

- `claude/CLAUDE.md`
- `claude/AGENTS.md`
- `claude/rules/common`
- `claude/agents`
- `claude/commands`
- `claude/hooks`
- `templates/claude-settings.public.json`

Do not copy auth, channel, session, project, telemetry, cache, or
`settings.local.json` state into this repo.

## Codex

Review these directories before applying:

- `codex/AGENTS.md`
- `codex/agents`
- `codex/hooks`
- `templates/codex-config.public.toml`

The live `~/.codex/config.toml` may contain MCP bearer tokens and local app
paths. Recreate those values manually from a secret manager instead of copying
the live file.

## Plugins

Plugin cache directories are not backed up. Use the inventories under
`claude/plugins` and `codex/plugins` to reinstall or enable plugins from their
marketplaces.
