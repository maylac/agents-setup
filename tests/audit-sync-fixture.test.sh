#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(/usr/bin/mktemp -d "$ROOT/tests/.tmp-audit.XXXXXX")"

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

REPO="$TEST_TMP/repo"
HOME_FIXTURE="$TEST_TMP/home"
mkdir -p \
  "$REPO/scripts" \
  "$REPO/manifests" \
  "$REPO/codex/hooks" \
  "$REPO/templates" \
  "$REPO/home" \
  "$REPO/claude/hooks" \
  "$REPO/claude/agents" \
  "$REPO/claude/rules/common" \
  "$REPO/claude/rules/typescript" \
  "$REPO/claude/rules/python" \
  "$REPO/claude/rules/swift" \
  "$REPO/claude/rules/kotlin" \
  "$HOME_FIXTURE/.claude/hooks" \
  "$HOME_FIXTURE/.claude/agents" \
  "$HOME_FIXTURE/.claude/rules" \
  "$HOME_FIXTURE/.claude/skills" \
  "$HOME_FIXTURE/.codex/hooks" \
  "$HOME_FIXTURE/.codex/agents" \
  "$HOME_FIXTURE/.codex/skills" \
  "$HOME_FIXTURE/.hermes/skills/hermes-local" \
  "$HOME_FIXTURE/.agents/skills/alpha" \
  "$HOME_FIXTURE/.agents/skills/source-command-demo" \
  "$TEST_TMP/tmp"

cp "$ROOT/scripts/audit-sync.sh" "$REPO/scripts/audit-sync.sh"

printf '{"version":1}\n' > "$REPO/manifests/ai-config-sync.json"
cat > "$REPO/manifests/skill-store-exceptions.json" <<'JSON'
{"version":1,"exceptions":[{"name":"hermes-local","source":"hermes-local","mirrors":["claude","codex"],"reason":"Fixture for a harness-managed local skill."}]}
JSON
printf '{"hooks":{}}\n' > "$REPO/templates/claude-settings.public.json"
printf 'home agents\n' > "$REPO/home/AGENTS.md"
printf 'claude\n' > "$REPO/claude/CLAUDE.md"
printf 'claude agents\n' > "$REPO/claude/AGENTS.md"
printf 'rtk\n' > "$REPO/claude/RTK.md"
printf 'hook\n' > "$REPO/claude/hooks/rtk-rewrite.sh"
cp "$REPO/claude/hooks/rtk-rewrite.sh" "$REPO/codex/hooks/rtk-rewrite.sh"
cp "$REPO/claude/hooks/rtk-rewrite.sh" "$HOME_FIXTURE/.claude/hooks/rtk-rewrite.sh"
cp "$REPO/codex/hooks/rtk-rewrite.sh" "$HOME_FIXTURE/.codex/hooks/rtk-rewrite.sh"

printf 'agent\n' > "$REPO/claude/agents/helper.md"
cp "$REPO/claude/agents/helper.md" "$HOME_FIXTURE/.claude/agents/helper.md"
printf 'name = "helper"\n' > "$HOME_FIXTURE/.codex/agents/helper.toml"

ln -s "$REPO/home/AGENTS.md" "$HOME_FIXTURE/AGENTS.md"
ln -s "$REPO/home/AGENTS.md" "$HOME_FIXTURE/CLAUDE.md"
ln -s "$REPO/claude/CLAUDE.md" "$HOME_FIXTURE/.claude/CLAUDE.md"
ln -s "$REPO/claude/AGENTS.md" "$HOME_FIXTURE/.claude/AGENTS.md"
ln -s "$REPO/claude/RTK.md" "$HOME_FIXTURE/.claude/RTK.md"
for lang in common typescript python swift kotlin; do
  ln -s "$REPO/claude/rules/$lang" "$HOME_FIXTURE/.claude/rules/$lang"
done
ln -s "../AGENTS.md" "$HOME_FIXTURE/.codex/AGENTS.md"

cat > "$REPO/codex/hooks.json" <<'JSON'
{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"$HOME/.codex/hooks/rtk-rewrite.sh"}]}]}}
JSON
printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"%s/.codex/hooks/rtk-rewrite.sh"}]}]}}\n' "$HOME_FIXTURE" > "$HOME_FIXTURE/.codex/hooks.json"
printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"%s/.claude/hooks/rtk-rewrite.sh"}]}],"Stop":[{"hooks":[{"command":"echo done"}]}]}}\n' "$HOME_FIXTURE" > "$HOME_FIXTURE/.claude/settings.json"

cat > "$HOME_FIXTURE/.agents/skills/alpha/SKILL.md" <<'SKILL'
---
name: alpha
description: Alpha fixture.
---
SKILL
cat > "$HOME_FIXTURE/.agents/skills/source-command-demo/SKILL.md" <<'SKILL'
---
name: source-command-demo
description: Source command fixture.
---
SKILL
ln -s "../../.agents/skills/alpha" "$HOME_FIXTURE/.claude/skills/alpha"
ln -s "../../.agents/skills/alpha" "$HOME_FIXTURE/.codex/skills/alpha"
ln -s "../../.agents/skills/source-command-demo" "$HOME_FIXTURE/.codex/skills/source-command-demo"
printf 'hermes managed\n' > "$HOME_FIXTURE/.hermes/skills/hermes-local/SKILL.md"
cp -R "$HOME_FIXTURE/.hermes/skills/hermes-local" "$HOME_FIXTURE/.claude/skills/hermes-local"
cp -R "$HOME_FIXTURE/.hermes/skills/hermes-local" "$HOME_FIXTURE/.codex/skills/hermes-local"

success_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/audit-sync.sh" 2>&1)"
assert_contains "$success_output" "ok: live Codex hook registration"
assert_contains "$success_output" "ok: canonical <-> Claude skills parity"
assert_contains "$success_output" "AI config sync audit passed."

printf 'drift\n' >> "$HOME_FIXTURE/.claude/skills/hermes-local/SKILL.md"
set +e
drift_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/audit-sync.sh" 2>&1)"
drift_status=$?
set -e
[ "$drift_status" -eq 1 ] || fail "expected Hermes-local exception drift audit to fail, got $drift_status"
assert_contains "$drift_output" "FAIL: ~/.claude/skills exception drift"
cp "$HOME_FIXTURE/.hermes/skills/hermes-local/SKILL.md" "$HOME_FIXTURE/.claude/skills/hermes-local/SKILL.md"

printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"%s/.codex/hooks/rtk-rewrite.sh"}]}],"Stop":[{"hooks":[{"command":"open -a Ghostty"}]}]}}\n' "$HOME_FIXTURE" > "$HOME_FIXTURE/.codex/hooks.json"

set +e
failure_output="$(HOME="$HOME_FIXTURE" TMPDIR="$TEST_TMP/tmp/" bash "$REPO/scripts/audit-sync.sh" 2>&1)"
failure_status=$?
set -e
[ "$failure_status" -eq 1 ] || fail "expected Ghostty Stop hook audit to fail, got $failure_status"
assert_contains "$failure_output" "FAIL: Codex Ghostty Stop hook present"

printf 'audit sync fixture tests passed.\n'
