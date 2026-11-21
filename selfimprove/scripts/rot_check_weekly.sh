#!/bin/zsh
# launchd (com.maylac.selfimprove-rot) から週次で呼ばれるラッパー。
# findings または巡回期限があれば macOS 通知を出し、古いレポートを刈る。
set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
SELFIMPROVE="$REPO_ROOT/selfimprove"
OUT=$(/usr/bin/python3 "$SELFIMPROVE/scripts/rot_check.py" --report-dir "$SELFIMPROVE/reports" 2>&1)
STATUS=$?
echo "$OUT"

if [ $STATUS -ne 0 ]; then
  SUMMARY=$(echo "$OUT" | grep '^rot_check:' | head -1)
  /usr/bin/osascript -e "display notification \"${SUMMARY} → /self-improve で対応\" with title \"selfimprove 週次チェック\"" 2>/dev/null || true
fi

REPORT_DIR="$SELFIMPROVE/reports"
REPORT="$REPORT_DIR/rot-$(date '+%Y-%m-%d').md"
WARN_COUNT=0
DUE_COUNT=0
if [ -f "$REPORT" ]; then
  WARN_COUNT=$(grep -cF -- '- [WARN]' "$REPORT" || true)
  DUE_COUNT=$(awk '
    /^## 巡回期限/ { in_due=1; next }
    /^## / { in_due=0 }
    in_due && /^- / { count++ }
    END { print count+0 }
  ' "$REPORT")
fi
SAME_CONTENT_WEEKS=$(/usr/bin/python3 - "$REPORT_DIR" "$REPORT" <<'PY'
import datetime as dt
import pathlib
import re
import sys

report_dir = pathlib.Path(sys.argv[1])
current = pathlib.Path(sys.argv[2])
date_pattern = re.compile(r"rot-(\d{4}-\d{2}-\d{2})\.md$")

def normalized(path):
    content = path.read_text(encoding="utf-8")
    # Count the current report and exact seven-day predecessors, ignoring only its generated heading date and numeric age counters.
    content = re.sub(r"(?m)^(# rot check )\d{4}-\d{2}-\d{2}$", r"\1<date>", content)
    content = re.sub(r"期限\d+日超過", "期限<age>日超過", content)
    content = re.sub(r"\d+日未更新", "<age>日未更新", content)
    return content

if not current.is_file():
    print(0)
    raise SystemExit

match = date_pattern.fullmatch(current.name)
if not match:
    print(0)
    raise SystemExit

current_date = dt.date.fromisoformat(match.group(1))
signature = normalized(current)
weeks = 1
while True:
    current_date -= dt.timedelta(days=7)
    prior = report_dir / f"rot-{current_date.isoformat()}.md"
    if not prior.is_file() or normalized(prior) != signature:
        break
    weeks += 1
print(weeks)
PY
)
SUMMARY="rot週次: WARN ${WARN_COUNT}件、期限超過 ${DUE_COUNT}件、同内容 ${SAME_CONTENT_WEEKS}週連続"
echo "$SUMMARY"
"$REPO_ROOT/agents/hooks/notify-mobile.sh" note selfimprove \
  "$SUMMARY" || true

# レポートは直近8週分だけ残す
ls -t "$SELFIMPROVE"/reports/rot-*.md 2>/dev/null | tail -n +9 | while read -r f; do
  rm -f "$f"
done

exit 0
