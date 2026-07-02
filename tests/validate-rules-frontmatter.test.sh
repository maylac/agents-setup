#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_TEST="$(mktemp -d)"

cleanup() {
  rm -rf "$TMPDIR_TEST"
}
trap cleanup EXIT

FIXTURE="$TMPDIR_TEST/repo"
mkdir -p "$FIXTURE/scripts" "$FIXTURE/skills/example" "$FIXTURE/claude/rules/python" "$TMPDIR_TEST/bin"

cp "$ROOT/scripts/validate.sh" "$FIXTURE/scripts/validate.sh"

cat > "$FIXTURE/scripts/audit-sync.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$FIXTURE/scripts/audit-sync.sh"

cat > "$FIXTURE/skills/example/SKILL.md" <<'SKILL'
---
name: example
description: Fixture skill for validate.sh tests.
---

# Example
SKILL

cat > "$FIXTURE/claude/rules/python/bad.md" <<'MD'
---
paths:
  - "**/*.py"
  - [
---

# Bad Rule
MD

cat > "$TMPDIR_TEST/bin/git" <<'SH'
#!/usr/bin/env bash
if [ "${1:-}" = "-C" ]; then
  shift 2
fi
if [ "${1:-}" = "diff" ] && [ "${2:-}" = "--check" ]; then
  exit 0
fi
printf 'unexpected git shim args: %s\n' "$*" >&2
exit 99
SH
chmod +x "$TMPDIR_TEST/bin/git"

set +e
output="$(PATH="$TMPDIR_TEST/bin:$PATH" bash "$FIXTURE/scripts/validate.sh" 2>&1)"
status=$?
set -e

if [ "$status" -eq 0 ]; then
  printf 'FAIL: validate.sh accepted invalid rules paths frontmatter\n' >&2
  printf '%s\n' "$output" >&2
  exit 1
fi

if ! grep -q 'invalid paths frontmatter YAML: claude/rules/python/bad.md' <<<"$output"; then
  printf 'FAIL: validate.sh failed for the wrong reason\n' >&2
  printf '%s\n' "$output" >&2
  exit 1
fi

printf 'validate rules frontmatter tests passed.\n'
