#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(/usr/bin/mktemp -d "$ROOT/tests/.tmp-sync-skills.XXXXXX")"

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

HOME_FIXTURE="$TEST_TMP/home"
mkdir -p \
  "$HOME_FIXTURE/.agents/skills/alpha" \
  "$HOME_FIXTURE/.agents/skills/source-command-demo" \
  "$HOME_FIXTURE/.agents/skills/update-docs" \
  "$HOME_FIXTURE/.agents/skills/replace-me" \
  "$HOME_FIXTURE/.agents/skills/.system" \
  "$HOME_FIXTURE/.claude/skills/source-command-demo" \
  "$HOME_FIXTURE/.codex/skills/replace-me" \
  "$HOME_FIXTURE/.codex/skills"

printf 'old real dir\n' > "$HOME_FIXTURE/.codex/skills/replace-me/README.md"
ln -s "../../.agents/skills/missing" "$HOME_FIXTURE/.codex/skills/stale"

dry_output="$(HOME="$HOME_FIXTURE" bash "$ROOT/scripts/sync-skills.local.sh" --dry-run)"
assert_contains "$dry_output" "DRY: ln -s \"../../.agents/skills/alpha\" \"$HOME_FIXTURE/.claude/skills/alpha\""
assert_contains "$dry_output" "dry_run=1"
[ ! -e "$HOME_FIXTURE/.claude/skills/alpha" ] || fail "dry-run created a Claude skill link"

output="$(HOME="$HOME_FIXTURE" bash "$ROOT/scripts/sync-skills.local.sh")"
assert_contains "$output" "dry_run=0"

[ -L "$HOME_FIXTURE/.claude/skills/alpha" ] || fail "Claude alpha skill link missing"
[ "$(readlink "$HOME_FIXTURE/.claude/skills/alpha")" = "../../.agents/skills/alpha" ] || fail "Claude alpha link target mismatch"
[ ! -e "$HOME_FIXTURE/.claude/skills/source-command-demo" ] || fail "source-command skill should be excluded from Claude mirror"
[ -L "$HOME_FIXTURE/.claude/skills/update-docs" ] || fail "migrated skill should be linked into Claude mirror"
[ -L "$HOME_FIXTURE/.codex/skills/update-docs" ] || fail "command-backed skill should be linked into Codex mirror"
[ -L "$HOME_FIXTURE/.codex/skills/source-command-demo" ] || fail "source-command skill should be linked into Codex mirror"
[ -L "$HOME_FIXTURE/.codex/skills/replace-me" ] || fail "real Codex skill directory should be replaced with symlink"
[ "$(readlink "$HOME_FIXTURE/.codex/skills/replace-me")" = "../../.agents/skills/replace-me" ] || fail "replacement symlink target mismatch"
[ ! -e "$HOME_FIXTURE/.codex/skills/stale" ] || fail "dangling symlink was not pruned"
[ ! -e "$HOME_FIXTURE/.claude/skills/.system" ] || fail "dot-prefixed canonical skill should be ignored for Claude"
[ ! -e "$HOME_FIXTURE/.codex/skills/.system" ] || fail "dot-prefixed canonical skill should be ignored for Codex"

printf 'sync skills local tests passed.\n'
