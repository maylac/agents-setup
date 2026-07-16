#!/usr/bin/env bash
set -euo pipefail
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:?HOME must be set}"
INSTRUCTIONS_ONLY=0

usage() {
  cat <<'USAGE'
Usage: scripts/backup.sh [--instructions-only]

Refresh the public-safe backup snapshot.

Options:
  --instructions-only  Refresh only home/AGENTS.md, home/CLAUDE.md,
                       claude/CLAUDE.md, claude/AGENTS.md, claude/RTK.md,
                       claude/rules/common, codex/AGENTS.md, and
                       codex/hooks.json.
USAGE
}

case "${1:-}" in
  "")
    ;;
  --instructions-only)
    INSTRUCTIONS_ONLY=1
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

sanitize_file() {
  local file="$1"
  grep -Iq . "$file" || return 0
  perl -0pi \
    -e 's#/Users/[A-Za-z0-9._-]+#\$HOME#g;' \
    -e 's#-Users-[A-Za-z0-9._-]+#-Users-[redacted-user]#g;' \
    -e 's#may\.lac1206\@gmail\.com#[redacted-email]#g;' \
    -e 's#gh[opsu]_[A-Za-z0-9_]+#[REDACTED_GITHUB_TOKEN]#g;' \
    -e 's#github_pat_[A-Za-z0-9_]+#[REDACTED_GITHUB_TOKEN]#g;' \
    -e 's#(Authorization[[:space:]]*=[[:space:]]*["'\'']?Bearer[[:space:]]+)[A-Za-z0-9._-]+#${1}[REDACTED_BEARER_TOKEN]#g;' \
    -e 's#(Authorization:[[:space:]]*Bearer[[:space:]]+)[A-Za-z0-9._-]+#${1}[REDACTED_BEARER_TOKEN]#g;' \
    "$file"
}

sanitize_tree() {
  local dir="$1"
  [ -d "$dir" ] || return 0
  while IFS= read -r -d '' file; do
    sanitize_file "$file"
  done < <(/usr/bin/find "$dir" -type f -print0)
}

sync_dir() {
  local src="$1"
  local dst="$2"
  shift 2
  [ -d "$src" ] || return 0
  if [ -d "$dst" ] && [ "$(cd -P "$src" && pwd)" = "$(cd -P "$dst" && pwd)" ]; then
    return 0
  fi
  mkdir -p "$dst"
  rsync -a --delete "$@" \
    --exclude='.git/' \
    --exclude='.agmsg/' \
    --exclude='.temp/' \
    --exclude='db/' \
    --exclude='node_modules/' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite3' \
    --exclude='*.sqlite-shm' \
    --exclude='*.sqlite-wal' \
    --exclude='*.log' \
    --exclude='history.jsonl' \
    --exclude='settings.local.json' \
    "$src/" "$dst/"
}

sync_file() {
  local src="$1"
  local dst="$2"
  [ -f "$src" ] || return 0
  if [ -e "$dst" ] && cmp -s "$src" "$dst"; then
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

sync_instruction_files() {
  mkdir -p "$ROOT/home" "$ROOT/claude/rules" "$ROOT/codex"

  sync_file "$HOME_DIR/AGENTS.md" "$ROOT/home/AGENTS.md"
  rm -f "$ROOT/home/CLAUDE.md"
  if [ -L "$HOME_DIR/CLAUDE.md" ]; then
    ln -s AGENTS.md "$ROOT/home/CLAUDE.md"
  else
    sync_file "$HOME_DIR/CLAUDE.md" "$ROOT/home/CLAUDE.md"
  fi

  sync_file "$HOME_DIR/.claude/CLAUDE.md" "$ROOT/claude/CLAUDE.md"
  sync_file "$HOME_DIR/.claude/AGENTS.md" "$ROOT/claude/AGENTS.md"
  sync_file "$HOME_DIR/.claude/RTK.md" "$ROOT/claude/RTK.md"
  sync_dir "$HOME_DIR/.claude/rules/common" "$ROOT/claude/rules/common"

  rm -f "$ROOT/codex/AGENTS.md"
  if [ -L "$HOME_DIR/.codex/AGENTS.md" ]; then
    ln -s ../home/AGENTS.md "$ROOT/codex/AGENTS.md"
  else
    sync_file "$HOME_DIR/.codex/AGENTS.md" "$ROOT/codex/AGENTS.md"
  fi

  sync_file "$HOME_DIR/.codex/hooks.json" "$ROOT/codex/hooks.json"
}

sanitize_instruction_files() {
  sanitize_tree "$ROOT/home"
  sanitize_file "$ROOT/claude/CLAUDE.md"
  sanitize_file "$ROOT/claude/AGENTS.md"
  sanitize_file "$ROOT/claude/RTK.md"
  sanitize_tree "$ROOT/claude/rules/common"
  [ -L "$ROOT/codex/AGENTS.md" ] || sanitize_file "$ROOT/codex/AGENTS.md"
  sanitize_file "$ROOT/codex/hooks.json"
}

write_codex_template() {
  cat > "$ROOT/templates/codex-config.public.toml" <<'TOML'
# Public-safe Codex config template.
# Do not paste live bearer tokens, auth files, sqlite state, or local cache paths.

approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.5"
model_reasoning_effort = "xhigh"

[tui]
status_line = [
    "model-with-reasoning",
    "current-dir",
    "git-branch",
    "context-remaining",
    "context-used",
    "five-hour-limit",
    "weekly-limit",
]
status_line_use_colors = true

[model_providers.fugu]
name = "Sakana Fugu"
base_url = "https://api.sakana.ai/v1"
env_key = "SAKANA_FUGU_API_KEY"
env_key_instructions = "Set SAKANA_FUGU_API_KEY in your shell or secret manager."
wire_api = "responses"

[plugins."github@openai-curated"]
enabled = true

[plugins."documents@openai-primary-runtime"]
enabled = true

[plugins."spreadsheets@openai-primary-runtime"]
enabled = true

[plugins."presentations@openai-primary-runtime"]
enabled = true

[plugins."notion@openai-curated"]
enabled = true

[plugins."google-calendar@openai-curated"]
enabled = true

[plugins."discord@claude-plugins-official"]
enabled = true

[plugins."imessage@claude-plugins-official"]
enabled = true

[plugins."codex@openai-codex"]
enabled = true

[plugins."frontend-design@claude-plugins-official"]
enabled = true

[plugins."pdf@openai-primary-runtime"]
enabled = true

[plugins."browser@openai-bundled"]
enabled = true

[plugins."chrome@openai-bundled"]
enabled = true

[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"

[mcp_servers.github.http_headers]
Authorization = "Bearer ${GITHUB_COPILOT_MCP_TOKEN}"
TOML
}

write_claude_settings_template() {
  if [ -f "$HOME_DIR/.claude/settings.json" ] && command -v jq >/dev/null 2>&1; then
    jq '{
      language,
      theme,
      includeCoAuthoredBy,
      remoteControlAtStartup,
      statusLine,
      hooks,
      enabledPlugins
    }' "$HOME_DIR/.claude/settings.json" > "$ROOT/templates/claude-settings.public.json"
    sanitize_file "$ROOT/templates/claude-settings.public.json"
  fi
}

write_plugin_inventory() {
  {
    printf '# Claude Plugins\n\n'
    printf 'Generated from `claude plugin list`.\n\n'
    if command -v claude >/dev/null 2>&1; then
      printf '```text\n'
      claude plugin list | sed -e 's/[[:space:]]*$//' || true
      printf '```\n'
    else
      printf 'Claude CLI was not available during backup.\n'
    fi
  } > "$ROOT/claude/plugins/installed-plugins.md"

  {
    printf '# Codex Plugins\n\n'
    printf 'Generated from `codex plugin list`, filtered to installed plugins.\n\n'
    if command -v codex >/dev/null 2>&1; then
      printf '```text\n'
      codex plugin list | awk '/installed, enabled|installed, disabled/ { print }' | sed -e 's/[[:space:]]*$//' || true
      printf '```\n'
    else
      printf 'Codex CLI was not available during backup.\n'
    fi
  } > "$ROOT/codex/plugins/installed-plugins.md"

  sanitize_file "$ROOT/claude/plugins/installed-plugins.md"
  sanitize_file "$ROOT/codex/plugins/installed-plugins.md"
}

write_inventory() {
  {
    printf '# Inventory\n\n'
    printf 'Generated by `scripts/backup.sh` on %s.\n\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '## Included sources\n\n'
    printf '%s\n' '- `~/.agents/skills` excluding runtime state, `gstack`, and `capafy-publisher`'
    printf '%s\n' '- `~/AGENTS.md` and `~/CLAUDE.md` symlink state'
    printf '%s\n' '- `~/.claude/CLAUDE.md`, `~/.claude/AGENTS.md`, `~/.claude/RTK.md`, and `~/.claude/rules/common`'
    printf '%s\n' '- `~/.claude/agents`'
    printf '%s\n' '- `~/.claude/hooks` excluding trust-hash state'
    printf '%s\n' '- `~/.claude/output-styles`'
    printf '%s\n' '- `~/.codex/AGENTS.md` normalized to point at the repo home snapshot'
    printf '%s\n' '- `~/.codex/hooks.json` with local home paths sanitized'
    printf '%s\n' '- `~/.codex/agents`'
    printf '%s\n\n' '- `~/.codex/hooks` excluding trust-hash state'
    printf '## Excluded sources\n\n'
    printf '%s\n' '- `~/.agents/skills/gstack`: upstream repo; restore from `https://github.com/garrytan/gstack.git`'
    printf '%s\n' '- `~/.agents/skills/capafy-publisher`: contains auth/configuration and publishing workflow code requiring manual review'
    printf '%s\n' '- `~/.agents/skills/agmsg/db` and `.agmsg`: local message state'
    printf '%s\n' '- `~/.claude` sessions, projects, tasks, telemetry, cache, channels, auth, and backups'
    printf '%s\n\n' '- `~/.codex` auth, sessions, sqlite DBs, generated images, plugin caches, memories, logs, and app-server state'
    printf '## Skill snapshot\n\n'
    /usr/bin/find "$ROOT/skills" -mindepth 1 -maxdepth 1 -type d -print | sed "s#^$ROOT/skills/#- #g" | sort
  } > "$ROOT/manifests/inventory.md"
}

require_command cp
require_command rsync
require_command perl
require_command grep

mkdir -p "$ROOT/home" "$ROOT/skills" "$ROOT/claude/agents" "$ROOT/claude/hooks" "$ROOT/claude/output-styles" \
  "$ROOT/claude/plugins" "$ROOT/codex/agents" "$ROOT/codex/hooks" "$ROOT/codex/plugins" \
  "$ROOT/manifests" "$ROOT/templates"

sync_instruction_files

if [ "$INSTRUCTIONS_ONLY" -eq 1 ]; then
  sanitize_instruction_files
  printf 'Instruction snapshot refreshed in %s\n' "$ROOT"
  exit 0
fi

# --copy-unsafe-links: canonical entries may be symlinks to skills developed
# elsewhere (e.g. fable-escalation lives in this repo). Copying such a link
# verbatim would plant a self-referential symlink loop inside the repo, so
# materialize out-of-tree links while keeping in-tree relative links intact.
# /agmsg/run/ holds per-session watcher pids/watermarks — runtime state, not config.
sync_dir "$HOME_DIR/.agents/skills" "$ROOT/skills" --copy-unsafe-links --exclude=/agmsg/run/
rm -rf "$ROOT/skills/gstack" "$ROOT/skills/capafy-publisher" \
  "$ROOT/skills/defense-in-depth" "$ROOT/skills/root-cause-tracing"

sync_dir "$HOME_DIR/.claude/agents" "$ROOT/claude/agents"
# --copy-links: live hooks are symlinks into ~/.agents/hooks (canonical store),
# which this backup does not mirror; snapshot the resolved content instead so
# the repo copy stays self-contained and audit-sync cmp checks keep working.
sync_dir "$HOME_DIR/.claude/hooks" "$ROOT/claude/hooks" --copy-links
rm -f "$ROOT/claude/hooks/.rtk-hook.sha256"
sync_dir "$HOME_DIR/.claude/output-styles" "$ROOT/claude/output-styles" --copy-links

sync_dir "$HOME_DIR/.codex/agents" "$ROOT/codex/agents"
sync_dir "$HOME_DIR/.codex/hooks" "$ROOT/codex/hooks" --copy-links
rm -f "$ROOT/codex/hooks/.rtk-hook.sha256"

if [ -f "$HOME_DIR/.agents/sync-skills.sh" ]; then
  cp "$HOME_DIR/.agents/sync-skills.sh" "$ROOT/scripts/sync-skills.local.sh"
fi

write_codex_template
write_claude_settings_template
write_plugin_inventory

sanitize_tree "$ROOT/skills"
sanitize_instruction_files
sanitize_tree "$ROOT/claude"
sanitize_tree "$ROOT/codex"
sanitize_tree "$ROOT/templates"

write_inventory
sanitize_file "$ROOT/manifests/inventory.md"

printf 'Backup snapshot refreshed in %s\n' "$ROOT"
