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

echo "validate private paths tests passed."
