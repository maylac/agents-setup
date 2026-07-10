#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0
VALIDATE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/agents-setup-validate.XXXXXX")"

cleanup() {
  rm -rf "$VALIDATE_TMP"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  failed=1
}

check_no_matches() {
  local label="$1"
  local pattern="$2"
  local out="$VALIDATE_TMP/rg.out"
  if rg -n --hidden --glob '!.git/**' --glob '!**/.git/**' --glob '!*.png' --glob '!*.jpg' --glob '!*.webp' "$pattern" "$ROOT" >"$out" 2>/dev/null; then
    printf '%s\n' "$label" >&2
    sed -n '1,80p' "$out" >&2
    failed=1
  fi
}

check_no_paths() {
  local out="$VALIDATE_TMP/paths.out"
  if /usr/bin/find "$ROOT" -path "$ROOT/.git" -prune -o \
    \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.sqlite-shm' -o -name '*.sqlite-wal' -o -name '.env' \) -print |
    rg . >"$out"; then
    printf 'Runtime/private files are present:\n' >&2
    sed -n '1,80p' "$out" >&2
    failed=1
  fi
}

check_skills() {
  local skill base
  while IFS= read -r -d '' skill; do
    base="$(basename "$skill")"
    case "$base" in .*) continue;; esac  # dot-prefixed dirs (e.g. one-off .backup-* snapshots) aren't skills
    if [ ! -f "$skill/SKILL.md" ] && [ ! -f "$skill/skill.md" ]; then
      fail "skill lacks SKILL.md or skill.md: ${skill#$ROOT/}"
    fi
  done < <(/usr/bin/find "$ROOT/skills" -mindepth 1 -maxdepth 1 -type d -print0)
}

check_json() {
  if [ -f "$ROOT/templates/claude-settings.public.json" ]; then
    jq empty "$ROOT/templates/claude-settings.public.json" || fail "invalid JSON: templates/claude-settings.public.json"
  fi
  if [ -f "$ROOT/codex/hooks.json" ]; then
    jq empty "$ROOT/codex/hooks.json" || fail "invalid JSON: codex/hooks.json"
  fi
  if [ -f "$ROOT/manifests/ai-config-sync.json" ]; then
    jq empty "$ROOT/manifests/ai-config-sync.json" || fail "invalid JSON: manifests/ai-config-sync.json"
  fi
}

check_shell() {
  local script
  while IFS= read -r -d '' script; do
    bash -n "$script" || fail "shell syntax error: ${script#$ROOT/}"
  done < <(/usr/bin/find "$ROOT/scripts" -type f -name '*.sh' -print0)
}

# RL-5: rules/ lint — dead "See skill:" references, invalid paths frontmatter,
# and banned fixed-coverage-percentage language.
check_rules_lint() {
  local rules_dir="$ROOT/claude/rules"
  [ -d "$rules_dir" ] || return 0

  local f name
  while IFS= read -r -d '' f; do
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      if [ ! -d "$ROOT/skills/$name" ]; then
        fail "rules file references nonexistent skill \`$name\`: ${f#$ROOT/}"
      fi
    done < <(/usr/bin/grep -oE 'See skill: `[a-zA-Z0-9._-]+`' "$f" | sed -E 's/See skill: `([^`]+)`/\1/')
  done < <(/usr/bin/find "$rules_dir" -type f -name '*.md' -print0)

  while IFS= read -r -d '' f; do
    if head -1 "$f" | /usr/bin/grep -q '^---$' &&
       awk 'NR > 1 && /^---$/ { exit } NR > 1 { print }' "$f" | /usr/bin/grep -q '^paths:'; then
      if command -v ruby >/dev/null 2>&1; then
        if ! awk 'NR > 1 && /^---$/ { exit } NR > 1 { print }' "$f" | ruby -ryaml -e 'YAML.safe_load(STDIN.read)' >/dev/null 2>&1; then
          fail "invalid paths frontmatter YAML: ${f#$ROOT/}"
        fi
      elif python3 -c "import sys, yaml" >/dev/null 2>&1; then
        if ! awk 'NR > 1 && /^---$/ { exit } NR > 1 { print }' "$f" | python3 -c "import sys, yaml; yaml.safe_load(sys.stdin)" >/dev/null 2>&1; then
          fail "invalid paths frontmatter YAML: ${f#$ROOT/}"
        fi
      else
        fail "missing YAML parser for paths frontmatter: ${f#$ROOT/}"
      fi
    fi
  done < <(/usr/bin/find "$rules_dir" -type f -name '*.md' -print0)

  check_no_matches 'Fixed coverage percentage in rules (should defer to repo target):' 'Target [0-9]+%\+ .*coverage'
}

check_no_paths
check_skills
check_json
check_shell
check_rules_lint

if [ -d "$HOME/.claude" ] && [ -d "$HOME/.codex" ] && [ -d "$HOME/.agents" ]; then
  bash "$ROOT/scripts/audit-sync.sh" || failed=1
else
  printf 'SKIP: live harness sync audit (Claude/Codex/agents homes unavailable)\n'
fi

check_no_matches 'Private home paths remain:' '(/Users/(maylac|gotasa+ki)|-Users-(maylac|gotasa+ki))'
check_no_matches 'Email address remains:' 'may\.lac1206@gmail\.com'
check_no_matches 'GitHub token-like value remains:' '(gho_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9_]{20,}|ghu_[A-Za-z0-9_]{20,}|ghs_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})'
# sk- must not be preceded by an alphanumeric so prose like "task-specific-ai-functions" doesn't match.
check_no_matches 'OpenAI/Sakana token-like value remains:' '((^|[^A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}|SAKANA_[A-Z0-9_]*=[A-Za-z0-9_-]{16,})'
check_no_matches 'Bearer token-like value remains:' 'Bearer[[:space:]]+[A-Za-z0-9._-]{20,}'

git -C "$ROOT" diff --check || failed=1

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Validation passed.\n'
