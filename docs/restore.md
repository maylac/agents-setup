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

Skills whose canonical entry is a symlink into an upstream clone (restore the
clone first, then re-link; `install.sh --apply` leaves existing symlinks alone):

- `session-triage`: `git clone https://github.com/chaenmasahiro0425/claude-session-triage ~/workspace/claude-session-triage`,
  then `ln -s ~/workspace/claude-session-triage/skills/session-triage ~/.agents/skills/session-triage`.
  Config lives in `~/.claude/session-triage/config.json` (seed from `config.example.json`).
  Runs only in the Claude desktop app Code tab (needs `mcp__ccd_session_mgmt__*`); the Codex mirror loads but stops.

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

## Permission boundary templates

These are reviewable templates. Apply them only after the human approves the exact change. The installer does not install either permissions template.

### Claude Code

`templates/claude-settings.permissions.json` contains the proposed `permissions` and `sandbox` values. The executing agent backs up the live file and generates a candidate that merges only these sections, but leaves the live file untouched. The agent reports the changed-key summary without printing config values. The human reviews that intent from GitHub Mobile; only after the exact `APPROVED:` reply does the agent replace the live file. Existing hooks, unrelated top-level keys, unrelated permission keys, and extra sandbox keys are preserved. Permission and sandbox arrays are additive and deduplicated, except the obsolete blanket `Bash(launchctl:*)` entry is removed from `permissions.allow`; template values are otherwise added. The template's `defaultMode` and sandbox scalar keys are updated.

```sh
cp -p "$HOME/.claude/settings.json" "$HOME/.claude/settings.json.backup.$(date +%Y%m%d%H%M%S)"
python3 - "$HOME/.claude/settings.json" "$PWD/templates/claude-settings.permissions.json" "$HOME/.claude/settings.json.candidate" <<'PYTHON'
import json, sys
from pathlib import Path
live, template, candidate = map(Path, sys.argv[1:])
current = json.loads(live.read_text())
proposed = json.loads(template.read_text())
permissions = current.setdefault('permissions', {})
for key, value in proposed['permissions'].items():
    if isinstance(value, list):
        existing = permissions.get(key, [])
        if key == 'allow':
            existing = [item for item in existing if item != 'Bash(launchctl:*)']
        permissions[key] = list(dict.fromkeys([*existing, *value]))
    else:
        permissions[key] = value
sandbox = current.setdefault('sandbox', {})
def merge(existing, updates):
    for key, value in updates.items():
        if isinstance(value, dict):
            existing[key] = merge(existing.get(key, {}), value)
        elif isinstance(value, list):
            existing[key] = list(dict.fromkeys([*existing.get(key, []), *value]))
        else:
            existing[key] = value
    return existing
current['sandbox'] = merge(sandbox, proposed['sandbox'])
candidate.write_text(json.dumps(current, indent=2, ensure_ascii=False) + '\n')
print('Candidate created. Updated keys: permissions.allow, permissions.ask, permissions.deny, permissions.defaultMode, sandbox.*')
print('Removed obsolete Bash(launchctl:*) from permissions.allow.')
PYTHON
```

The printed summary names changed keys only; it does not print hooks, credentials, or unrelated settings. The candidate stays local and no full-config diff is printed or sent. After the agent reports the backup, candidate result, and fixed changed-key summary, the human approves the exact replacement from GitHub Mobile; the agent then runs `cp -p "$HOME/.claude/settings.json.candidate" "$HOME/.claude/settings.json"`.

### Codex

`templates/codex-config.workspace-write.toml` is a partial template. Its `$HOME` strings are literal placeholders; TOML does not expand `$HOME` or `~`. The executing agent backs up the live config and creates a candidate copy, but leaves the live config untouched. The agent edits only top-level `approval_policy` and `sandbox_mode`, plus `[sandbox_workspace_write]` keys `network_access` and `writable_roots`. Render each `$HOME` placeholder in the `writable_roots` values to the absolute home path. Replace the entire existing value of each listed key, including a multiline `writable_roots` array; do not leave old array continuation lines behind. Preserve every other key, table, MCP entry, and local setting.

```sh
cp -p "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.backup.$(date +%Y%m%d%H%M%S)"
cp -p "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.candidate"
python3 -c 'import os,sys; print(sys.stdin.read().replace("$HOME", os.path.expanduser("~")), end="")' < "$PWD/templates/codex-config.workspace-write.toml" > "$HOME/.codex/config.workspace-write.rendered.toml"
cat "$HOME/.codex/config.workspace-write.rendered.toml"
# Agent: edit only the four listed keys in config.toml.candidate; leave config.toml untouched.
command -v python3.12 >/dev/null || { echo "python3.12 with tomllib required; candidate not validated" >&2; exit 1; }
python3.12 - "$HOME/.codex/config.toml.candidate" <<'PYTHON'
import sys, tomllib
from pathlib import Path
config = tomllib.loads(Path(sys.argv[1]).read_text())
print({
    'approval_policy': config['approval_policy'],
    'sandbox_mode': config['sandbox_mode'],
    'sandbox_workspace_write.network_access': config['sandbox_workspace_write']['network_access'],
    'sandbox_workspace_write.writable_roots': config['sandbox_workspace_write']['writable_roots'],
})
PYTHON
```

The final command parses the full candidate TOML and prints only the four changed values, so it validates syntax without exposing MCP or other config values. If `python3.12` is unavailable, stop before replacement; do not install a parser for this step. After the agent reports the backup, successful parse, and four changed-key summary, the human approves the exact replacement from GitHub Mobile; the agent then runs `cp -p "$HOME/.codex/config.toml.candidate" "$HOME/.codex/config.toml"`.

After any approved instruction-file installation, the intended command is:

```sh
scripts/install.sh --apply-instructions --instructions-only
```

This applies instruction files only, not either permissions template. Review first with `scripts/install.sh --instructions-only`.
