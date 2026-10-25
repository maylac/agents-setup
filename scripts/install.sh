#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY_SKILLS=0
APPLY_INSTRUCTIONS=0
APPLY_ASSETS=0
INSTRUCTIONS_ONLY=0
ASSETS_ONLY=0
BACKUP_DIR=""

usage() {
  cat <<'USAGE'
Usage: scripts/install.sh [--apply] [--apply-instructions] [--apply-assets]
                          [--instructions-only|--assets-only]

Dry-run restore checks for the public-safe agent setup snapshot.

Options:
  --apply              Create missing skill symlinks in ~/.agents/skills.
  --apply-instructions Back up current instruction files, then replace them
                       with symlinks to this repo's canonical snapshots.
  --apply-assets       Back up and copy public-safe Claude/Codex agent and
                       hook files from this repo.
  --instructions-only  Show only instruction-file comparisons.
  --assets-only        Show only agent and hook file comparisons.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply)
      APPLY_SKILLS=1
      ;;
    --apply-instructions)
      APPLY_INSTRUCTIONS=1
      ;;
    --apply-assets)
      APPLY_ASSETS=1
      ;;
    --instructions-only)
      INSTRUCTIONS_ONLY=1
      ;;
    --assets-only)
      ASSETS_ONLY=1
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
  shift
done

if [ "$INSTRUCTIONS_ONLY" -eq 1 ] && [ "$ASSETS_ONLY" -eq 1 ]; then
  printf '%s\n' 'ERROR: --instructions-only and --assets-only cannot be combined.' >&2
  exit 2
fi
if [ "$INSTRUCTIONS_ONLY" -eq 1 ] && [ "$APPLY_ASSETS" -eq 1 ]; then
  printf '%s\n' 'ERROR: --apply-assets cannot be combined with --instructions-only.' >&2
  exit 2
fi
if [ "$ASSETS_ONLY" -eq 1 ] && { [ "$APPLY_INSTRUCTIONS" -eq 1 ] || [ "$APPLY_SKILLS" -eq 1 ]; }; then
  printf '%s\n' 'ERROR: --assets-only cannot apply instructions or skills.' >&2
  exit 2
fi

compare_file() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [ ! -e "$src" ]; then
    printf 'missing snapshot: %s (%s)\n' "$src" "$label"
    return 0
  fi

  if [ ! -e "$dest" ]; then
    printf 'would copy missing: %s -> %s\n' "$src" "$dest"
    return 0
  fi

  if cmp -s "$src" "$dest"; then
    printf 'same: %s\n' "$dest"
    return 0
  fi

  printf 'diff: %s\n' "$label"
  diff -u "$dest" "$src" | sed -n '1,120p' || true
}

materialize_home() {
  awk -v home="$HOME" '{ gsub(/\$HOME/, home); print }' "$1"
}

compare_materialized_file() {
  local src="$1"
  local dest="$2"
  local label="$3"
  local tmp

  if [ ! -e "$src" ]; then
    printf 'missing snapshot: %s (%s)\n' "$src" "$label"
    return 0
  fi

  if [ ! -e "$dest" ]; then
    printf 'would materialize missing: %s -> %s\n' "$src" "$dest"
    return 0
  fi

  tmp="$(mktemp)"
  materialize_home "$src" > "$tmp"
  if cmp -s "$tmp" "$dest"; then
    printf 'same materialized: %s\n' "$dest"
    rm -f "$tmp"
    return 0
  fi

  printf 'diff materialized: %s\n' "$label"
  diff -u "$dest" "$tmp" | sed -n '1,120p' || true
  rm -f "$tmp"
}

compare_symlink() {
  local dest="$1"
  local expected="$2"
  local label="$3"

  if [ -L "$dest" ]; then
    local current
    current="$(readlink "$dest")"
    if [ "$current" = "$expected" ]; then
      printf 'same symlink: %s -> %s\n' "$dest" "$current"
    else
      printf 'would relink: %s -> %s (currently %s)\n' "$dest" "$expected" "$current"
    fi
    return 0
  fi

  if [ -e "$dest" ]; then
    printf 'would replace existing non-symlink with symlink: %s -> %s (%s)\n' "$dest" "$expected" "$label"
  else
    printf 'would create symlink: %s -> %s (%s)\n' "$dest" "$expected" "$label"
  fi
}

backup_target() {
  local dest="$1"
  [ -e "$dest" ] || [ -L "$dest" ] || return 0

  if [ -z "$BACKUP_DIR" ]; then
    BACKUP_DIR="$HOME/.agents-setup-backups/$(date +%Y%m%d-%H%M%S)"
  fi

  local rel
  rel="${dest#$HOME/}"
  mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
  cp -a "$dest" "$BACKUP_DIR/$rel"
}

apply_symlink() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    printf 'already linked: %s -> %s\n' "$dest" "$src"
    return 0
  fi

  backup_target "$dest"
  rm -rf "$dest"
  mkdir -p "$(dirname "$dest")"
  ln -s "$src" "$dest"
  printf 'linked: %s -> %s (%s)\n' "$dest" "$src" "$label"
}

apply_materialized_file() {
  local src="$1"
  local dest="$2"
  local label="$3"
  local tmp

  tmp="$(mktemp)"
  materialize_home "$src" > "$tmp"

  if [ -e "$dest" ] && cmp -s "$tmp" "$dest"; then
    printf 'already materialized: %s (%s)\n' "$dest" "$label"
    rm -f "$tmp"
    return 0
  fi

  backup_target "$dest"
  mkdir -p "$(dirname "$dest")"
  cp "$tmp" "$dest"
  rm -f "$tmp"
  printf 'materialized: %s -> %s (%s)\n' "$src" "$dest" "$label"
}

apply_snapshot_file() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    printf 'already copied: %s (%s)\n' "$dest" "$label"
    return 0
  fi

  backup_target "$dest"
  mkdir -p "$(dirname "$dest")"
  rm -f "$dest"
  cp -p "$src" "$dest"
  printf 'copied: %s -> %s (%s)\n' "$src" "$dest" "$label"
}

walk_asset_files() {
  local callback="$1"
  local mapping repo_dir live_dir path rel
  for mapping in \
    'claude/agents:.claude/agents' \
    'codex/agents:.codex/agents' \
    'claude/hooks:.claude/hooks' \
    'codex/hooks:.codex/hooks'; do
    repo_dir="${mapping%%:*}"
    live_dir="${mapping#*:}"
    [ -d "$ROOT/$repo_dir" ] || continue
    while IFS= read -r -d '' path; do
      rel="${path#"$ROOT/$repo_dir/"}"
      "$callback" "$path" "$HOME/$live_dir/$rel" "$repo_dir/$rel"
    done < <(/usr/bin/find "$ROOT/$repo_dir" -type f ! -name '*.pyc' -print0 | sort -z)
  done
}

show_asset_file() {
  compare_file "$1" "$2" "$3"
}

show_asset_dry_run() {
  printf 'Agent and hook restore dry-run:\n'
  walk_asset_files show_asset_file
}

apply_assets() {
  printf '\nApplying public-safe agent and hook files:\n'
  walk_asset_files apply_snapshot_file
  if [ -n "$BACKUP_DIR" ]; then
    printf 'Backed up replaced asset files under: %s\n' "$BACKUP_DIR"
  fi
}

show_instruction_dry_run() {
  printf 'Instruction restore dry-run:\n'
  compare_file "$ROOT/home/AGENTS.md" "$HOME/AGENTS.md" '~/AGENTS.md'
  compare_symlink "$HOME/CLAUDE.md" "$ROOT/home/AGENTS.md" '~/CLAUDE.md'
  compare_file "$ROOT/claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md" '~/.claude/CLAUDE.md'
  compare_file "$ROOT/claude/AGENTS.md" "$HOME/.claude/AGENTS.md" '~/.claude/AGENTS.md'
  compare_file "$ROOT/claude/RTK.md" "$HOME/.claude/RTK.md" '~/.claude/RTK.md'

  for rule_dir in common typescript python swift kotlin; do
    if [ -d "$ROOT/claude/rules/$rule_dir" ]; then
      while IFS= read -r -d '' rule; do
        compare_file "$rule" "$HOME/.claude/rules/$rule_dir/$(basename "$rule")" "~/.claude/rules/$rule_dir/$(basename "$rule")"
      done < <(/usr/bin/find "$ROOT/claude/rules/$rule_dir" -type f -name '*.md' -print0 | sort -z)
    fi
  done

  compare_symlink "$HOME/.codex/AGENTS.md" '../AGENTS.md' '~/.codex/AGENTS.md'
  compare_materialized_file "$ROOT/codex/hooks.json" "$HOME/.codex/hooks.json" '~/.codex/hooks.json'

  printf '\nCanonical symlink plan:\n'
  compare_symlink "$HOME/AGENTS.md" "$ROOT/home/AGENTS.md" '~/AGENTS.md'
  compare_symlink "$HOME/CLAUDE.md" "$ROOT/home/AGENTS.md" '~/CLAUDE.md'
  compare_symlink "$HOME/.claude/CLAUDE.md" "$ROOT/claude/CLAUDE.md" '~/.claude/CLAUDE.md'
  compare_symlink "$HOME/.claude/AGENTS.md" "$ROOT/claude/AGENTS.md" '~/.claude/AGENTS.md'
  compare_symlink "$HOME/.claude/RTK.md" "$ROOT/claude/RTK.md" '~/.claude/RTK.md'
  compare_symlink "$HOME/.claude/output-styles" "$ROOT/claude/output-styles" '~/.claude/output-styles'
  compare_symlink "$HOME/.claude/rules/common" "$ROOT/claude/rules/common" '~/.claude/rules/common'
  compare_symlink "$HOME/.claude/rules/typescript" "$ROOT/claude/rules/typescript" '~/.claude/rules/typescript'
  compare_symlink "$HOME/.claude/rules/python" "$ROOT/claude/rules/python" '~/.claude/rules/python'
  compare_symlink "$HOME/.claude/rules/swift" "$ROOT/claude/rules/swift" '~/.claude/rules/swift'
  compare_symlink "$HOME/.claude/rules/kotlin" "$ROOT/claude/rules/kotlin" '~/.claude/rules/kotlin'
  compare_symlink "$HOME/.codex/AGENTS.md" '../AGENTS.md' '~/.codex/AGENTS.md'
  compare_symlink "$HOME/.agents/hooks/notify-mobile.sh" "$ROOT/agents/hooks/notify-mobile.sh" '~/.agents/hooks/notify-mobile.sh'
  compare_symlink "$HOME/.codex/herdr-agent-state.sh" "$ROOT/codex/herdr-agent-state.sh" '~/.codex/herdr-agent-state.sh'
  printf 'materialized file: %s -> %s (%s)\n' "$ROOT/codex/hooks.json" "$HOME/.codex/hooks.json" '~/.codex/hooks.json'
}

apply_instruction_symlinks() {
  printf '\nApplying canonical instruction symlinks:\n'
  apply_symlink "$ROOT/home/AGENTS.md" "$HOME/AGENTS.md" '~/AGENTS.md'
  apply_symlink "$ROOT/home/AGENTS.md" "$HOME/CLAUDE.md" '~/CLAUDE.md'
  apply_symlink "$ROOT/claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md" '~/.claude/CLAUDE.md'
  apply_symlink "$ROOT/claude/AGENTS.md" "$HOME/.claude/AGENTS.md" '~/.claude/AGENTS.md'
  apply_symlink "$ROOT/claude/RTK.md" "$HOME/.claude/RTK.md" '~/.claude/RTK.md'
  apply_symlink "$ROOT/claude/output-styles" "$HOME/.claude/output-styles" '~/.claude/output-styles'
  apply_symlink "$ROOT/claude/rules/common" "$HOME/.claude/rules/common" '~/.claude/rules/common'
  apply_symlink "$ROOT/claude/rules/typescript" "$HOME/.claude/rules/typescript" '~/.claude/rules/typescript'
  apply_symlink "$ROOT/claude/rules/python" "$HOME/.claude/rules/python" '~/.claude/rules/python'
  apply_symlink "$ROOT/claude/rules/swift" "$HOME/.claude/rules/swift" '~/.claude/rules/swift'
  apply_symlink "$ROOT/claude/rules/kotlin" "$HOME/.claude/rules/kotlin" '~/.claude/rules/kotlin'
  apply_symlink '../AGENTS.md' "$HOME/.codex/AGENTS.md" '~/.codex/AGENTS.md'
  apply_symlink "$ROOT/agents/hooks/notify-mobile.sh" "$HOME/.agents/hooks/notify-mobile.sh" '~/.agents/hooks/notify-mobile.sh'
  apply_symlink "$ROOT/codex/herdr-agent-state.sh" "$HOME/.codex/herdr-agent-state.sh" '~/.codex/herdr-agent-state.sh'
  apply_materialized_file "$ROOT/codex/hooks.json" "$HOME/.codex/hooks.json" '~/.codex/hooks.json'

  if [ -n "$BACKUP_DIR" ]; then
    printf 'Backed up replaced instruction files under: %s\n' "$BACKUP_DIR"
  fi
}

sync_skills() {
  local target="${HOME}/.agents/skills"

  printf 'Target skill directory: %s\n' "$target"

  if [ "$APPLY_SKILLS" -eq 1 ]; then
    mkdir -p "$target"
  fi

  while IFS= read -r -d '' skill; do
    local name
    local dest
    name="$(basename "$skill")"
    case "$name" in .*) continue;; esac
    dest="$target/$name"
    if [ -L "$dest" ]; then
      local current
      current="$(readlink "$dest")"
      printf 'exists symlink: %s -> %s\n' "$dest" "$current"
      continue
    fi
    if [ -e "$dest" ]; then
      printf 'skip existing non-symlink: %s\n' "$dest"
      continue
    fi
    if [ "$APPLY_SKILLS" -eq 1 ]; then
      ln -s "$skill" "$dest"
      printf 'linked: %s -> %s\n' "$dest" "$skill"
    else
      printf 'would link: %s -> %s\n' "$dest" "$skill"
    fi
  done < <(/usr/bin/find "$ROOT/skills" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

  if [ "$APPLY_SKILLS" -eq 0 ]; then
    printf '\nSkill dry-run only. Re-run with --apply to create missing skill symlinks.\n'
  fi
}

if [ "$ASSETS_ONLY" -eq 0 ]; then
  show_instruction_dry_run
fi

if [ "$APPLY_INSTRUCTIONS" -eq 1 ]; then
  apply_instruction_symlinks
fi

if [ "$INSTRUCTIONS_ONLY" -eq 0 ]; then
  printf '\n'
  show_asset_dry_run
fi

if [ "$APPLY_ASSETS" -eq 1 ]; then
  apply_assets
fi

if [ "$INSTRUCTIONS_ONLY" -eq 0 ] && [ "$ASSETS_ONLY" -eq 0 ]; then
  printf '\n'
  sync_skills
fi

printf '\nReview docs/restore.md before applying hooks, plugins, or main settings.\n'
