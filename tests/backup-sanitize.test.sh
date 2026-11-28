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
cp "$ROOT/scripts/portable-codex-hooks.jq" "$REPO/scripts/portable-codex-hooks.jq"

printf 'fixture instructions\n' > "$HOME_FIXTURE/AGENTS.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/CLAUDE.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/CLAUDE.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/AGENTS.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.claude/RTK.md"
printf 'fixture instructions\n' > "$HOME_FIXTURE/.codex/AGENTS.md"
printf '%s\n' \
  '{"plain":"/Users/fixture-user/.codex/hooks/run.sh","escaped":"\/Users\/fixture-user\/portable\/bridge","regex":"keep \/regex\/literal","hooks":{"Stop":[{"hooks":[{"command":"\/Users\/fixture-user\/.vibe-island\/bin\/bridge"},{"command":"$HOME/.codex/runcat-hook.py"},{"command":"echo portable"}]}]}}' \
  > "$HOME_FIXTURE/.codex/hooks.json"
jq --arg command "/bin/sh -c 'rex __internal session-start --agent codex --feature-session-naming=false 2>/dev/null || true'" \
  '.hooks.SessionStart = [{"hooks":[{"command":$command,"timeout":5,"type":"command"}]},{"hooks":[{"command":"echo other startup","timeout":5,"type":"command"}]}]' \
  "$HOME_FIXTURE/.codex/hooks.json" > "$HOME_FIXTURE/.codex/hooks.tmp"
mv "$HOME_FIXTURE/.codex/hooks.tmp" "$HOME_FIXTURE/.codex/hooks.json"

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
if grep -Fq 'rex __internal session-start' "$sanitized"; then
  fail 'Mac-local Rex SessionStart command remains in portable snapshot'
fi
jq -e '.hooks.SessionStart | length == 1 and .[0].hooks[0].command == "echo other startup"' "$sanitized" >/dev/null ||
  fail 'unrelated SessionStart hook was removed from portable snapshot'

cp "$sanitized" "$TEST_TMP/codex-hooks.before-duplicate.json"
cp "$HOME_FIXTURE/.codex/hooks.json" "$TEST_TMP/live-hooks.before-duplicate.json"
jq '.hooks.SessionStart += [.["hooks"].SessionStart[0]]' "$HOME_FIXTURE/.codex/hooks.json" \
  > "$HOME_FIXTURE/.codex/hooks.tmp"
mv "$HOME_FIXTURE/.codex/hooks.tmp" "$HOME_FIXTURE/.codex/hooks.json"
set +e
duplicate_backup_output="$(HOME="$HOME_FIXTURE" bash "$REPO/scripts/backup.sh" --instructions-only 2>&1)"
duplicate_backup_status=$?
set -e
[ "$duplicate_backup_status" -ne 0 ] || fail 'duplicate exact Rex groups should fail the backup'
grep -Fq 'duplicate exact Rex SessionStart groups' <<<"$duplicate_backup_output" ||
  fail 'duplicate Rex backup failure did not identify the cause'
cmp -s "$TEST_TMP/codex-hooks.before-duplicate.json" "$sanitized" ||
  fail 'failed duplicate Rex backup replaced the previous snapshot'
cp "$TEST_TMP/live-hooks.before-duplicate.json" "$HOME_FIXTURE/.codex/hooks.json"

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
