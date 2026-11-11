#!/usr/bin/env bash
# validate.sh must reject a private home path even when the username is split
# so this test file never contains the literal value.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

FIXTURE="$TMPDIR_TEST/repo"
mkdir -p "$FIXTURE/scripts" "$FIXTURE/docs" "$FIXTURE/skills/example" "$FIXTURE/.claude/worktrees/sibling"
git -C "$FIXTURE" init -q
printf -- '---\nname: example\ndescription: Fixture skill.\n---\n\n# Example\n' > "$FIXTURE/skills/example/SKILL.md"
cp "$ROOT/scripts/validate.sh" "$FIXTURE/scripts/validate.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FIXTURE/scripts/audit-sync.sh"
chmod +x "$FIXTURE/scripts/audit-sync.sh"

leak="$(printf '/Users/gotasa%saki/Library/x' s)"

# 1. A sibling worktree under .claude/worktrees must be ignored.
printf 'see %s\n' "$leak" > "$FIXTURE/.claude/worktrees/sibling/note.md"
printf '# clean\n' > "$FIXTURE/docs/clean.md"
if ! HOME="$TMPDIR_TEST/home" bash "$FIXTURE/scripts/validate.sh" >"$TMPDIR_TEST/out1" 2>&1; then
  echo "FAIL: validate.sh should pass when the leak is only in a sibling worktree"; cat "$TMPDIR_TEST/out1"; exit 1
fi

# 2. The same path in tracked content must fail.
printf 'see %s\n' "$leak" > "$FIXTURE/docs/leak.md"
if HOME="$TMPDIR_TEST/home" bash "$FIXTURE/scripts/validate.sh" >"$TMPDIR_TEST/out2" 2>&1; then
  echo "FAIL: validate.sh accepted a private home path"; cat "$TMPDIR_TEST/out2"; exit 1
fi
grep -q 'Private home paths remain' "$TMPDIR_TEST/out2" || { echo "FAIL: wrong failure reason"; cat "$TMPDIR_TEST/out2"; exit 1; }

# 3. A minimal legacy snapshot without dispatcher files or Python tests still validates.
LEGACY="$TMPDIR_TEST/legacy"
mkdir -p "$LEGACY/scripts" "$LEGACY/docs" "$LEGACY/skills" "$LEGACY/templates"
git -C "$LEGACY" init -q
cp "$ROOT/scripts/validate.sh" "$LEGACY/scripts/validate.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$LEGACY/scripts/audit-sync.sh"
chmod +x "$LEGACY/scripts/audit-sync.sh"
if ! HOME="$TMPDIR_TEST/home" bash "$LEGACY/scripts/validate.sh" >"$TMPDIR_TEST/out3" 2>&1; then
  echo "FAIL: minimal legacy fixture without dispatcher sources should pass"; cat "$TMPDIR_TEST/out3"; exit 1
fi

# 4. If either dispatcher source exists, missing peer files and checks must fail.
mkdir -p "$LEGACY/docs/grok-bot"
printf '# Dispatcher\n' > "$LEGACY/docs/grok-bot/dispatcher-instructions.md"
if HOME="$TMPDIR_TEST/home" bash "$LEGACY/scripts/validate.sh" >"$TMPDIR_TEST/out4" 2>&1; then
  echo "FAIL: validator accepted an incomplete dispatcher source set"; cat "$TMPDIR_TEST/out4"; exit 1
fi
grep -q 'phone dispatcher source or required checks are missing' "$TMPDIR_TEST/out4" || { echo "FAIL: wrong dispatcher fixture failure reason"; cat "$TMPDIR_TEST/out4"; exit 1; }

echo "validate private paths and legacy worktree tests passed."
