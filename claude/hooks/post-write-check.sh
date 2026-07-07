#!/bin/bash
# PostToolUse hook (Edit|Write matcher). Advisory-only: never blocks, never exits non-zero.
#
# Two independent checks, gated by the edited file's path:
#   1. myLife/scripts/**/*.py or agents-setup/**/*.py -> ruff check (warning only)
#   2. myLife/wiki/pages/content/**                    -> publish_safety.py
#      (implements myLife/CLAUDE.md's documented rule: "公開前に python3
#      scripts/wiki-lint/publish_safety.py を必ず実行". The script itself is
#      advisory by design ("外部投稿の可否を自動判断せず、人間レビューが必要な
#      リスクだけを列挙する") -- this hook only makes sure it actually runs and
#      is visible, it does not change that philosophy.)
set -u

input=$(cat)
file_path=$(printf '%s' "$input" | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass" 2>/dev/null)

[[ -z "$file_path" ]] && exit 0

case "$file_path" in
  */workspace/myLife/scripts/*.py|*/workspace/agents-setup/*.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff check "$file_path" 2>&1 | sed 's/^/[lint] /' >&2
    fi
    ;;
  */workspace/myLife/wiki/pages/content/*)
    repo_root="$HOME/workspace/myLife"
    if [[ -f "$repo_root/scripts/wiki-lint/publish_safety.py" ]]; then
      (cd "$repo_root" && python3 scripts/wiki-lint/publish_safety.py) 2>&1 | sed 's/^/[publish_safety] /' >&2
    fi
    ;;
esac

exit 0
