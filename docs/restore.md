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

The backup removes the single exact Mac-local Rex `SessionStart` group and
Vibe Island and RunCat registrations from portable `codex/hooks.json`. Rex is
local to this Mac. Vibe Island and RunCat are Mac-managed hooks and must not be
enabled inside WSL. The audit rejects duplicate Rex groups and any other
unexplained hook drift while permitting those documented live-only entries.

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
it. The single exact Mac-local Rex `SessionStart` group and Vibe Island and
RunCat registrations are excluded from the portable snapshot. Duplicate exact
Rex groups make the backup fail without replacing the previous snapshot.

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

These are reviewable templates. The installer does not install them. For Claude Code, create and review a candidate before applying any approved change.

### Claude Code

`templates/claude-settings.permissions.json` contains only the permission list additions and two filesystem read-deny additions for this change. The candidate merge changes only `permissions.allow`, `permissions.ask`, `permissions.deny`, and `sandbox.filesystem.denyRead`. It adds template list entries without duplicates and removes only `Bash` and `Bash(launchctl:*)` from `permissions.allow`. It retains all existing deny rules and preserves all other keys, including the current default mode, sandbox settings, unrelated asks, hooks, and top-level extensions. It writes a mode-`0600` candidate atomically and never replaces the source. Its output contains only the dotted leaf names that actually changed. The procedure below uses paths rooted at `$HOME`; it does not expand private paths into the public template.

```sh
python3 - "$HOME/.claude/settings.json" "$PWD/templates/claude-settings.permissions.json" "$HOME/.claude/settings.json.candidate" <<'PYTHON'
import json, os, sys, tempfile
from pathlib import Path

source, template, candidate = map(Path, sys.argv[1:])
if source.resolve() == candidate.resolve():
    raise ValueError('source and candidate must be different files')
current = json.loads(source.read_text(encoding='utf-8'))
proposed = json.loads(template.read_text(encoding='utf-8'))
before = json.loads(json.dumps(current))

permissions = current.setdefault('permissions', {})
if not isinstance(permissions, dict):
    raise TypeError('permissions must be an object')
proposed_permissions = proposed['permissions']
for key in ('allow', 'ask', 'deny'):
    existing = permissions.setdefault(key, [])
    if not isinstance(existing, list):
        raise TypeError(f'permissions.{key} must be an array')
    if key == 'allow':
        existing = [item for item in existing if item not in ('Bash', 'Bash(launchctl:*)')]
    permissions[key] = list(dict.fromkeys([*existing, *proposed_permissions[key]]))

sandbox = current.setdefault('sandbox', {})
if not isinstance(sandbox, dict):
    raise TypeError('sandbox must be an object')
filesystem = sandbox.setdefault('filesystem', {})
if not isinstance(filesystem, dict):
    raise TypeError('sandbox.filesystem must be an object')
deny_read = filesystem.setdefault('denyRead', [])
if not isinstance(deny_read, list):
    raise TypeError('sandbox.filesystem.denyRead must be an array')
filesystem['denyRead'] = list(dict.fromkeys([*deny_read, *proposed['sandbox']['filesystem']['denyRead']]))

changed = []
for dotted in ('permissions.allow', 'permissions.ask', 'permissions.deny', 'sandbox.filesystem.denyRead'):
    old, new = before, current
    for part in dotted.split('.'):
        old = old.get(part) if isinstance(old, dict) else None
        new = new.get(part) if isinstance(new, dict) else None
    if old != new:
        changed.append(dotted)

payload = (json.dumps(current, indent=2, ensure_ascii=False) + '\n').encode()
fd, temporary = tempfile.mkstemp(prefix=f'.{candidate.name}.', dir=candidate.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, candidate)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
for key in changed:
    print(key)
PYTHON
```

An existing deny rule stays in effect if an added ask rule also matches. Resolve any such overlap separately before relying on mobile approval.

The output lists actual changed leaf keys only. Do not print or send a full-config diff. Review the candidate locally. After approval of that exact candidate, apply it with `cp -p "$HOME/.claude/settings.json.candidate" "$HOME/.claude/settings.json"`.

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
