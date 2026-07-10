#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(/usr/bin/mktemp -d "$ROOT/tests/.tmp-rtk-hook.XXXXXX")"

cleanup() {
  rm -rf "$TEST_TMP"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_empty() {
  local value="$1"
  local label="$2"
  [ -z "$value" ] || {
    printf '%s\n' "$value" >&2
    fail "$label should be empty"
  }
}

BIN="$TEST_TMP/bin"
mkdir -p "$BIN"

cat > "$BIN/rtk" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version)
    printf 'rtk 0.23.0\n'
    exit 0
    ;;
  rewrite)
    case "${2:-}" in
      "git status")
        printf 'rtk git status\n'
        exit 0
        ;;
      "git push origin main")
        printf 'rtk git push origin main\n'
        exit 0
        ;;
      "git push --force origin main")
        printf 'rtk git push --force origin main\n'
        exit 0
        ;;
      "needs approval")
        printf 'rtk needs approval\n'
        exit 3
        ;;
      "plain command")
        exit 1
        ;;
      "denied command")
        exit 2
        ;;
    esac
    ;;
esac
exit 99
SH
chmod +x "$BIN/rtk"

allow_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"git status","description":"keep me"}}
JSON
)"
jq -e '.hookSpecificOutput.permissionDecision == "allow"' <<<"$allow_output" >/dev/null || fail "allow rewrite did not auto-allow"
jq -e '.hookSpecificOutput.updatedInput.command == "rtk git status"' <<<"$allow_output" >/dev/null || fail "allow rewrite command mismatch"
jq -e '.hookSpecificOutput.updatedInput.description == "keep me"' <<<"$allow_output" >/dev/null || fail "updated input did not preserve sibling fields"

push_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"git push origin main"}}
JSON
)"
jq -e '.hookSpecificOutput.updatedInput.command == "rtk git push origin main"' <<<"$push_output" >/dev/null || fail "push rewrite command mismatch"
jq -e '.hookSpecificOutput | has("permissionDecision") | not' <<<"$push_output" >/dev/null || fail "push rewrite should require caller approval"

force_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"git push --force origin main"}}
JSON
)"
jq -e '.hookSpecificOutput.permissionDecision == "deny"' <<<"$force_output" >/dev/null || fail "force push should be denied"

ask_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"needs approval"}}
JSON
)"
jq -e '.hookSpecificOutput.updatedInput.command == "rtk needs approval"' <<<"$ask_output" >/dev/null || fail "ask rewrite command mismatch"
jq -e '.hookSpecificOutput | has("permissionDecision") | not' <<<"$ask_output" >/dev/null || fail "ask rewrite should not auto-allow"

pass_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"plain command"}}
JSON
)"
assert_empty "$pass_output" "pass-through rewrite"

deny_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{"command":"denied command"}}
JSON
)"
assert_empty "$deny_output" "deny-rule pass-through"

missing_command_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" <<'JSON'
{"tool_input":{}}
JSON
)"
assert_empty "$missing_command_output" "missing command input"

cat > "$BIN/rtk" <<'SH'
#!/usr/bin/env bash
case "${1:-}" in
  --version)
    printf 'rtk 0.22.9\n'
    exit 0
    ;;
  rewrite)
    printf 'rewrite should not be called\n' >&2
    exit 99
    ;;
esac
exit 99
SH
chmod +x "$BIN/rtk"

old_output="$(PATH="$BIN:$PATH" bash "$ROOT/codex/hooks/rtk-rewrite.sh" 2>&1 <<'JSON'
{"tool_input":{"command":"git status"}}
JSON
)"
grep -Fq "too old (need >= 0.23.0)" <<<"$old_output" || {
  printf '%s\n' "$old_output" >&2
  fail "old rtk version warning missing"
}

printf 'rtk rewrite hook tests passed.\n'
