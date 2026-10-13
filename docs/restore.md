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
- `codex/hooks.json`

The intended symlink shape is:

```text
~/AGENTS.md -> <repo>/home/AGENTS.md
~/CLAUDE.md -> AGENTS.md
~/.claude/CLAUDE.md -> <repo>/claude/CLAUDE.md
~/.claude/AGENTS.md -> <repo>/claude/AGENTS.md
~/.claude/rules/common -> <repo>/claude/rules/common
~/.codex/AGENTS.md -> ../AGENTS.md
```

The live `~/.codex/hooks.json` is not symlinked. It is materialized from
`codex/hooks.json` with `$HOME` expanded so the active Codex hook trust state
can continue to refer to the live file path.

The backup intentionally removes Vibe Island and RunCat registrations from the
portable `codex/hooks.json`. They are Mac-managed hooks and must not be enabled
inside WSL. The Mac audit permits those two documented live-only additions but
still rejects any other unexplained hook drift.

Check Claude/Codex paired behavior after restore:

```sh
scripts/audit-sync.sh
```

## Agent and Hook Files

Preview the public-safe agent definitions and hook scripts separately:

```sh
scripts/install.sh --assets-only
```

After reviewing the paths and platform dependencies, copy them into the live
Claude/Codex homes:

```sh
scripts/install.sh --apply-assets --assets-only
```

Existing destination files are backed up under
`~/.agents-setup-backups/<timestamp>/`. The copy is additive: files that exist
only in the live home are not deleted. A snapshotted Herdr hook may be copied,
but the Surface/Linux Herdr installation remains its owner and may regenerate
it. Vibe Island and RunCat registration is excluded from the portable snapshot.

`compact-plus` is a Codex-only symlink to the separately restored
`~/workspace/tools/compact-plus` repository and must be recreated from its
owning installation source.

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
- `claude/output-styles`
- `claude/hooks`
- `templates/claude-settings.public.json`

Do not copy auth, channel, session, project, telemetry, cache, or
`settings.local.json` state into this repo.

Claude `settings.json` is kept as a live mutable file. The public template is a
restore guide; the audit checks the shared behavior that must match Codex.
The generated template excludes macOS sound commands, Homebrew Moshi, Vibe
Island, and Agent Notch hooks, and moves git push / PR creation rules into the
explicit-approval list. Re-add platform integrations only after their
Surface/Linux commands exist.

## Codex

Review these directories before applying:

- `codex/AGENTS.md`
- `codex/hooks.json`
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
