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

`templates/claude-settings.permissions.json` contains the proposed `permissions` and `sandbox` values. Back up the live file, generate a candidate that merges only these sections, inspect the diff, and replace the live file only after approval. Existing hooks, unrelated top-level keys, unrelated permission keys, and extra sandbox keys are preserved. Permission arrays are additive and deduplicated; the template's `defaultMode` and sandbox keys are updated.

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
        permissions[key] = list(dict.fromkeys([*permissions.get(key, []), *value]))
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
PYTHON
diff -u "$HOME/.claude/settings.json" "$HOME/.claude/settings.json.candidate"
```

After reviewing the candidate and confirming the backup, the approved replacement command is `cp -p "$HOME/.claude/settings.json.candidate" "$HOME/.claude/settings.json"`. Do not replace the complete settings file with the partial template.

### Codex

`templates/codex-config.workspace-write.toml` is a partial template. Its `$HOME` strings are literal placeholders; TOML does not expand `$HOME` or `~`. Back up the live config, render placeholders to absolute paths, and generate a candidate that changes only top-level `approval_policy` and `sandbox_mode`, and `sandbox_workspace_write.network_access` and `sandbox_workspace_write.writable_roots`. Every other line, MCP entry, table, and local setting is preserved.

```sh
cp -p "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.backup.$(date +%Y%m%d%H%M%S)"
python3 - "$HOME/.codex/config.toml" "$PWD/templates/codex-config.workspace-write.toml" "$HOME/.codex/config.toml.candidate" <<'PYTHON'
import os, re, sys
from pathlib import Path
live, template, candidate = map(Path, sys.argv[1:])
values = {}
for line in template.read_text().splitlines():
    match = re.match(r'^(approval_policy|sandbox_mode|network_access|writable_roots)\s*=\s*(.*)$', line)
    if match:
        values[match.group(1)] = match.group(2).replace('$HOME', os.path.abspath(os.path.expanduser('~')))
lines = live.read_text().splitlines(keepends=True)
def replace_key(section, key, value):
    global lines
    header = '[sandbox_workspace_write]'
    if section == 'top':
        begin, end = 0, next((i for i, row in enumerate(lines) if row.lstrip().startswith('[')), len(lines))
    else:
        try:
            begin = next(i for i, row in enumerate(lines) if row.strip() == header)
        except StopIteration:
            if lines and not lines[-1].endswith('\n'): lines[-1] += '\n'
            lines.extend(['\n', header + '\n'])
            begin = len(lines) - 1
        end = next((i for i in range(begin + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*=')
    found = next((i for i in range(begin, end) if pattern.match(lines[i])), None)
    rendered = f'{key} = {value}\n'
    if found is None:
        lines.insert(end, rendered)
    else:
        lines[found] = rendered
for key in ('approval_policy', 'sandbox_mode'):
    replace_key('top', key, values[key])
for key in ('network_access', 'writable_roots'):
    replace_key('sandbox', key, values[key])
candidate.write_text(''.join(lines))
PYTHON
diff -u "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.candidate"
```

After reviewing the candidate and confirming the backup, the approved replacement command is `cp -p "$HOME/.codex/config.toml.candidate" "$HOME/.codex/config.toml"`.

After any approved instruction-file installation, the intended command is:

```sh
scripts/install.sh --apply-instructions --instructions-only
```

This applies instruction files only, not either permissions template. Review first with `scripts/install.sh --instructions-only`.
