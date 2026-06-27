#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  failed=1
}

check_no_matches() {
  local label="$1"
  local pattern="$2"
  if rg -n --hidden --glob '!.git/**' --glob '!**/.git/**' --glob '!*.png' --glob '!*.jpg' --glob '!*.webp' "$pattern" "$ROOT" >/tmp/agents-setup-rg.out 2>/dev/null; then
    printf '%s\n' "$label" >&2
    sed -n '1,80p' /tmp/agents-setup-rg.out >&2
    failed=1
  fi
}

check_no_paths() {
  if /usr/bin/find "$ROOT" -path "$ROOT/.git" -prune -o \
    \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.sqlite-shm' -o -name '*.sqlite-wal' -o -name '.env' \) -print |
    rg . >/tmp/agents-setup-paths.out; then
    printf 'Runtime/private files are present:\n' >&2
    sed -n '1,80p' /tmp/agents-setup-paths.out >&2
    failed=1
  fi
}

check_skills() {
  local skill
  while IFS= read -r -d '' skill; do
    if [ ! -f "$skill/SKILL.md" ] && [ ! -f "$skill/skill.md" ]; then
      fail "skill lacks SKILL.md or skill.md: ${skill#$ROOT/}"
    fi
  done < <(/usr/bin/find "$ROOT/skills" -mindepth 1 -maxdepth 1 -type d -print0)
}

check_json() {
  if [ -f "$ROOT/templates/claude-settings.public.json" ]; then
    jq empty "$ROOT/templates/claude-settings.public.json" || fail "invalid JSON: templates/claude-settings.public.json"
  fi
}

check_shell() {
  local script
  while IFS= read -r -d '' script; do
    bash -n "$script" || fail "shell syntax error: ${script#$ROOT/}"
  done < <(/usr/bin/find "$ROOT/scripts" -type f -name '*.sh' -print0)
}

check_no_paths
check_skills
check_json
check_shell

check_no_matches 'Private home paths remain:' '(/Users/(maylac|gotasaki)|-Users-(maylac|gotasaki))'
check_no_matches 'Email address remains:' 'may\.lac1206@gmail\.com'
check_no_matches 'GitHub token-like value remains:' '(gho_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9_]{20,}|ghu_[A-Za-z0-9_]{20,}|ghs_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})'
check_no_matches 'OpenAI/Sakana token-like value remains:' '(sk-[A-Za-z0-9_-]{20,}|SAKANA_[A-Z0-9_]*=[A-Za-z0-9_-]{16,})'
check_no_matches 'Bearer token-like value remains:' 'Bearer[[:space:]]+[A-Za-z0-9._-]{20,}'

git -C "$ROOT" diff --check || failed=1

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Validation passed.\n'
