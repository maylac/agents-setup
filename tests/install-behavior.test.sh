#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(/usr/bin/mktemp -d "$ROOT/tests/.tmp-install.XXXXXX")"

cleanup() {
  rm -rf "$TEST_TMP"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  grep -Fq "$needle" <<<"$haystack" || {
    printf '%s\n' "$haystack" >&2
    fail "expected output to contain: $needle"
  }
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  if grep -Fq "$needle" <<<"$haystack"; then
    printf '%s\n' "$haystack" >&2
    fail "expected output not to contain: $needle"
  fi
}

REPO="$TEST_TMP/repo"
HOME_FIXTURE="$TEST_TMP/home"
mkdir -p \
  "$REPO/scripts" \
  "$REPO/home" \
  "$REPO/claude/rules/common" \
  "$REPO/claude/rules/typescript" \
  "$REPO/claude/rules/python" \
  "$REPO/claude/rules/swift" \
  "$REPO/claude/rules/kotlin" \
  "$REPO/codex" \
  "$REPO/skills/alpha" \
  "$REPO/skills/existing" \
  "$REPO/skills/.scratch" \
  "$HOME_FIXTURE/.codex" \
  "$HOME_FIXTURE/.agents/skills/existing" \
  "$TEST_TMP/tmp"

cp "$ROOT/scripts/install.sh" "$REPO/scripts/install.sh"

printf 'home agents\n' > "$REPO/home/AGENTS.md"
printf 'claude\n' > "$REPO/claude/CLAUDE.md"
printf 'claude agents\n' > "$REPO/claude/AGENTS.md"
printf 'rtk\n' > "$REPO/claude/RTK.md"
printf 'rule\n' > "$REPO/claude/rules/common/rule.md"
printf 'skill\n' > "$REPO/skills/alpha/SKILL.md"
printf 'skill\n' > "$REPO/skills/existing/SKILL.md"
printf 'hidden\n' > "$REPO/skills/.scratch/SKILL.md"
printf 'keep existing\n' > "$HOME_FIXTURE/.agents/skills/existing/README.md"

cat > "$REPO/codex/hooks.json" <<'JSON'
{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"$HOME/.codex/hooks/rtk-rewrite.sh"}]}]}}
JSON
printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"%s/.codex/hooks/rtk-rewrite.sh"}]}]}}\n' "$HOME_FIXTURE" > "$HOME_FIXTURE/.codex/hooks.json"

instructions_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/install.sh" --instructions-only)"
assert_contains "$instructions_output" "same materialized: $HOME_FIXTURE/.codex/hooks.json"
assert_not_contains "$instructions_output" "Target skill directory:"

set +e
invalid_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/install.sh" --bogus 2>&1)"
invalid_status=$?
set -e
[ "$invalid_status" -eq 2 ] || fail "expected invalid option to exit 2, got $invalid_status"
assert_contains "$invalid_output" "Usage: scripts/install.sh"

apply_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/install.sh" --apply)"
assert_contains "$apply_output" "linked: $HOME_FIXTURE/.agents/skills/alpha -> $REPO/skills/alpha"
assert_contains "$apply_output" "skip existing non-symlink: $HOME_FIXTURE/.agents/skills/existing"

[ -L "$HOME_FIXTURE/.agents/skills/alpha" ] || fail "alpha skill was not linked"
[ "$(readlink "$HOME_FIXTURE/.agents/skills/alpha")" = "$REPO/skills/alpha" ] || fail "alpha symlink target mismatch"
[ -d "$HOME_FIXTURE/.agents/skills/existing" ] || fail "existing non-symlink directory was removed"
[ ! -L "$HOME_FIXTURE/.agents/skills/existing" ] || fail "existing non-symlink directory was replaced"
[ ! -e "$HOME_FIXTURE/.agents/skills/.scratch" ] || fail "dot-prefixed skill directory should not be linked"

printf 'install behavior tests passed.\n'
