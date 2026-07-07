#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:?HOME must be set}"
failed=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  failed=1
}

ok() {
  printf 'ok: %s\n' "$1"
}

require_file() {
  local path="$1"
  [ -e "$path" ] || fail "missing: $path"
}

expect_symlink() {
  local path="$1"
  local expected="$2"
  local label="$3"

  if [ ! -L "$path" ]; then
    fail "$label is not a symlink: $path"
    return
  fi

  local actual
  actual="$(readlink "$path")"
  if [ "$actual" != "$expected" ]; then
    fail "$label symlink mismatch: $path -> $actual, expected $expected"
    return
  fi

  ok "$label symlink"
}

expect_same_file() {
  local a="$1"
  local b="$2"
  local label="$3"

  if cmp -s "$a" "$b"; then
    ok "$label"
  else
    fail "$label differs: $a vs $b"
  fi
}

materialize_home() {
  awk -v home="$HOME_DIR" '{ gsub(/\$HOME/, home); print }' "$1"
}

expect_materialized_same() {
  local src="$1"
  local dest="$2"
  local label="$3"
  local tmp
  tmp="$(mktemp)"
  materialize_home "$src" > "$tmp"
  if cmp -s "$tmp" "$dest"; then
    ok "$label"
  else
    fail "$label differs after materializing \$HOME: $src vs $dest"
  fi
  rm -f "$tmp"
}

json_ok() {
  local path="$1"
  jq empty "$path" >/dev/null || fail "invalid JSON: $path"
}

json_has_hook_command() {
  local path="$1"
  local event="$2"
  local matcher="$3"
  local contains="$4"
  local label="$5"

  if jq -e --arg event "$event" --arg matcher "$matcher" --arg contains "$contains" '
    .hooks[$event] // []
    | any(
        ((.matcher // "") == $matcher or ($matcher == "" and has("matcher") | not))
        and ((.hooks // []) | any((.command // "") | contains($contains)))
      )
  ' "$path" >/dev/null; then
    ok "$label"
  else
    fail "$label missing in $path"
  fi
}

json_has_no_stop_ghostty() {
  local path="$1"
  local label="$2"

  if jq -e '
    (.hooks.Stop // []) | any((.hooks // []) | any((.command // "") | contains("Ghostty")))
  ' "$path" >/dev/null; then
    fail "$label present (should have been removed — Stop no longer steals focus)"
  else
    ok "$label absent"
  fi
}

require_file "$ROOT/manifests/ai-config-sync.json"
require_file "$ROOT/codex/hooks.json"
require_file "$ROOT/templates/claude-settings.public.json"
require_file "$HOME_DIR/.claude/settings.json"
require_file "$HOME_DIR/.codex/hooks.json"

json_ok "$ROOT/manifests/ai-config-sync.json"
json_ok "$ROOT/codex/hooks.json"
json_ok "$ROOT/templates/claude-settings.public.json"
json_ok "$HOME_DIR/.claude/settings.json"
json_ok "$HOME_DIR/.codex/hooks.json"

expect_symlink "$HOME_DIR/AGENTS.md" "$ROOT/home/AGENTS.md" "~/AGENTS.md"
expect_symlink "$HOME_DIR/CLAUDE.md" "$ROOT/home/AGENTS.md" "~/CLAUDE.md"
expect_symlink "$HOME_DIR/.claude/CLAUDE.md" "$ROOT/claude/CLAUDE.md" "~/.claude/CLAUDE.md"
expect_symlink "$HOME_DIR/.claude/AGENTS.md" "$ROOT/claude/AGENTS.md" "~/.claude/AGENTS.md"
expect_symlink "$HOME_DIR/.claude/RTK.md" "$ROOT/claude/RTK.md" "~/.claude/RTK.md"
expect_symlink "$HOME_DIR/.claude/rules/common" "$ROOT/claude/rules/common" "~/.claude/rules/common"
for lang in typescript python swift kotlin; do
  expect_symlink "$HOME_DIR/.claude/rules/$lang" "$ROOT/claude/rules/$lang" "~/.claude/rules/$lang"
done
expect_symlink "$HOME_DIR/.codex/AGENTS.md" "../AGENTS.md" "~/.codex/AGENTS.md"

expect_same_file "$ROOT/claude/hooks/rtk-rewrite.sh" "$ROOT/codex/hooks/rtk-rewrite.sh" "repo RTK hook pair"
expect_same_file "$ROOT/claude/hooks/rtk-rewrite.sh" "$HOME_DIR/.claude/hooks/rtk-rewrite.sh" "live Claude RTK hook"
expect_same_file "$ROOT/codex/hooks/rtk-rewrite.sh" "$HOME_DIR/.codex/hooks/rtk-rewrite.sh" "live Codex RTK hook"
expect_materialized_same "$ROOT/codex/hooks.json" "$HOME_DIR/.codex/hooks.json" "live Codex hook registration"

json_has_hook_command "$HOME_DIR/.claude/settings.json" "PreToolUse" "Bash" ".claude/hooks/rtk-rewrite.sh" "Claude RTK PreToolUse hook"
json_has_hook_command "$HOME_DIR/.codex/hooks.json" "PreToolUse" "Bash" ".codex/hooks/rtk-rewrite.sh" "Codex RTK PreToolUse hook"
json_has_no_stop_ghostty "$HOME_DIR/.claude/settings.json" "Claude Ghostty Stop hook"
json_has_no_stop_ghostty "$HOME_DIR/.codex/hooks.json" "Codex Ghostty Stop hook"

# --- Skill store 3-way parity (PS-3 / SF-4 / PS-0 / PS-1) ---
CANON_SKILLS="$HOME_DIR/.agents/skills"
CLAUDE_SKILLS="$HOME_DIR/.claude/skills"
CODEX_SKILLS="$HOME_DIR/.codex/skills"
# source-command-* is deliberately excluded from the Claude mirror (D5).
# chronicle is Codex-only (2026-07-07 skills audit): it cannot fire on Claude
# yet its long description would be injected into every session.
CLAUDE_EXCLUDE_PATTERN='^source-command-|^chronicle$'

skill_parity_check() {
  local agent_dir="$1"
  local label="$2"
  local exclude_pattern="${3:-}"
  local diff
  diff="$(comm -3 <(ls "$CANON_SKILLS" | sort) <(ls "$agent_dir" 2>/dev/null | /usr/bin/grep -v '^\.' | sort) \
    | { [ -n "$exclude_pattern" ] && /usr/bin/grep -v -E "$exclude_pattern" || cat; })"
  if [ -n "$diff" ]; then
    fail "$label parity mismatch:"$'\n'"$diff"
  else
    ok "$label parity"
  fi
}

skill_parity_check "$CLAUDE_SKILLS" "canonical <-> Claude skills" "$CLAUDE_EXCLUDE_PATTERN"
skill_parity_check "$CODEX_SKILLS" "canonical <-> Codex skills"

orphan_real_dirs_check() {
  local agent_dir="$1"
  local label="$2"
  local orphans
  orphans="$(/usr/bin/find "$agent_dir" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -print 2>/dev/null)"
  if [ -n "$orphans" ]; then
    fail "$label has real (non-symlink) skill directories bypassing the canonical store:"$'\n'"$orphans"
  else
    ok "$label has no orphan real directories"
  fi
}

orphan_real_dirs_check "$CLAUDE_SKILLS" "~/.claude/skills"
orphan_real_dirs_check "$CODEX_SKILLS" "~/.codex/skills"

dangling_symlinks_check() {
  local base="$1"
  local label="$2"
  local dead
  # ~/.claude/debug/latest is a Claude Code-managed "current log" pointer that is
  # legitimately absent between sessions — known-benign, excluded here.
  dead="$(/usr/bin/find "$base" -maxdepth 3 -type l ! -exec test -e {} \; -print 2>/dev/null | { /usr/bin/grep -v '/.claude/debug/latest$' || true; })"
  if [ -n "$dead" ]; then
    fail "$label has dangling symlinks:"$'\n'"$dead"
  else
    ok "$label has no dangling symlinks"
  fi
}

dangling_symlinks_check "$HOME_DIR/.claude" "~/.claude"
dangling_symlinks_check "$HOME_DIR/.codex" "~/.codex"
dangling_symlinks_check "$HOME_DIR/.agents" "~/.agents"

# --- SKILL.md frontmatter validity (SF-0 / SF-3) ---
skill_frontmatter_check() {
  local dir path name n d
  local bad=0
  for path in "$CANON_SKILLS"/*/SKILL.md; do
    [ -e "$path" ] || continue
    d="$(basename "$(dirname "$path")")"
    if [ ! -s "$path" ]; then
      fail "empty SKILL.md: $path"
      bad=1
      continue
    fi
    n="$(awk '/^name:/{sub(/^name:[ ]*/,""); gsub(/"/,""); print; exit}' "$path")"
    if [ -z "$n" ]; then
      fail "SKILL.md missing name: frontmatter: $path"
      bad=1
    elif [ "$n" != "$d" ]; then
      fail "SKILL.md name mismatch: $d -> $n"
      bad=1
    fi
  done
  [ "$bad" -eq 0 ] && ok "SKILL.md frontmatter (non-empty, name == dir) across canonical store"
}

skill_frontmatter_check

# --- Agents directory parity (AG-3) ---
# harness-optimizer is a documented Claude-only exception. Codex also keeps a
# pinned TOML superset for language/runtime specialists that Claude no longer
# loads globally (see manifests/ai-config-sync.json intentional_differences).
AGENTS_CODEX_EXCEPTIONS='^[[:space:]]*(architect|cpp-build-resolver|cpp-reviewer|doc-updater|docs-lookup|flutter-reviewer|go-build-resolver|go-reviewer|harness-optimizer|java-build-resolver|java-reviewer|kotlin-build-resolver|kotlin-reviewer|loop-operator|python-reviewer|pytorch-build-resolver|refactor-cleaner|rust-build-resolver|rust-reviewer|tdd-guide|typescript-reviewer)$'

agents_repo_live_parity_check() {
  local repo_dir="$ROOT/claude/agents"
  local live_dir="$HOME_DIR/.claude/agents"
  local diff
  diff="$(diff -rq "$repo_dir" "$live_dir" 2>&1 || true)"
  if [ -n "$diff" ]; then
    fail "claude/agents (repo) and ~/.claude/agents (live) differ — run scripts/backup.sh:"$'\n'"$diff"
  else
    ok "claude/agents repo <-> live parity"
  fi
}

agents_claude_codex_parity_check() {
  local claude_names codex_names diff
  claude_names="$(ls "$HOME_DIR/.claude/agents" | sed 's/\.md$//' | sort)"
  codex_names="$(ls "$HOME_DIR/.codex/agents" | sed 's/\.toml$//' | sort)"
  diff="$(comm -3 <(printf '%s\n' "$claude_names") <(printf '%s\n' "$codex_names") | { /usr/bin/grep -v -E "$AGENTS_CODEX_EXCEPTIONS" || true; })"
  if [ -n "$diff" ]; then
    fail "Claude <-> Codex agent name mismatch (undocumented):"$'\n'"$diff"
  else
    ok "Claude <-> Codex agent name parity"
  fi
}

agents_repo_live_parity_check
agents_claude_codex_parity_check

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'AI config sync audit passed.\n'
