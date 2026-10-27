#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(/usr/bin/mktemp -d "$ROOT/tests/.tmp-backup-sanitize.XXXXXX")"

cleanup() {
  rm -rf "$TEST_TMP"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

REPO="$TEST_TMP/repo"
HOME_FIXTURE="$TEST_TMP/home"
mkdir -p "$REPO/scripts" "$HOME_FIXTURE/.claude/rules/common" "$HOME_FIXTURE/.codex"
cp "$ROOT/scripts/backup.sh" "$REPO/scripts/backup.sh"

printf 'fixture instructions\n' > "$HOME_FIXTURE/AGENTS.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/CLAUDE.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/CLAUDE.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/AGENTS.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/RTK.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.codex/AGENTS.md"
printf '%s\n' \
  '{"plain":"/Users/fixture-user/.codex/hooks/run.sh","escaped":"\/Users\/fixture-user\/portable\/bridge","regex":"keep \/regex\/literal","hooks":{"Stop":[{"hooks":[{"command":"\/Users\/fixture-user\/.vibe-island\/bin\/bridge"},{"command":"$HOME/.codex/runcat-hook.py"},{"command":"echo portable"}]}]}}' \
  > "$HOME_FIXTURE/.codex/hooks.json"

cat > "$HOME_FIXTURE/.claude/settings.json" <<'JSON'
{
  "model": "claude-opus-5-5",
  "effortLevel": "high",
  "modelSettings": {
    "claude-opus-5-5": {"effortLevel": "medium"},
    "claude-sonnet-5": {"effortLevel": "medium"}
  },
  "promptSuggestionEnabled": false,
  "remoteControlAtStartup": true,
  "sandbox": {"enabled": true, "allowUnsandboxedCommands": false}
}
JSON

HOME="$HOME_FIXTURE" bash "$REPO/scripts/backup.sh" --instructions-only >/dev/null
sanitized="$REPO/codex/hooks.json"

[ "$(jq -r '.plain' "$sanitized")" = '$HOME/.codex/hooks/run.sh' ] ||
  fail 'plain macOS home path was not sanitized'
[ "$(jq -r '.escaped' "$sanitized")" = '$HOME/portable/bridge' ] ||
  fail 'JSON-escaped macOS home path was not sanitized'
[ "$(jq -r '.regex' "$sanitized")" = 'keep /regex/literal' ] ||
  fail 'unrelated escaped slash value was modified'
if grep -Fq 'fixture-user' "$sanitized"; then
  fail 'fixture username remains after sanitization'
fi
grep -Fq 'echo portable' "$sanitized" || fail 'portable Codex hook was removed'
if grep -Fq '.vibe-island' "$sanitized" || grep -Fq 'runcat-hook.py' "$sanitized"; then
  fail 'Mac-only Codex hook remains in portable snapshot'
fi

HOME="$HOME_FIXTURE" bash "$REPO/scripts/backup.sh" >/dev/null
claude_settings="$REPO/templates/claude-settings.public.json"
jq -e '
  .model == "claude-opus-5-5" and
  .effortLevel == "high" and
  .modelSettings["claude-opus-5-5"].effortLevel == "medium" and
  .modelSettings["claude-sonnet-5"].effortLevel == "medium" and
  .promptSuggestionEnabled == false and
  .remoteControlAtStartup == true and
  .sandbox.enabled == true and
  .sandbox.allowUnsandboxedCommands == false
' "$claude_settings" >/dev/null || fail 'Claude model settings were not projected as expected'

jq 'del(.effortLevel)' "$HOME_FIXTURE/.claude/settings.json" > "$HOME_FIXTURE/.claude/settings.tmp"
mv "$HOME_FIXTURE/.claude/settings.tmp" "$HOME_FIXTURE/.claude/settings.json"
HOME="$HOME_FIXTURE" bash "$REPO/scripts/backup.sh" >/dev/null
jq -e '(has("effortLevel") | not)' "$claude_settings" >/dev/null ||
  fail 'absent legacy effortLevel should be omitted from the backup snapshot'

printf 'backup sanitizer tests passed.\n'
