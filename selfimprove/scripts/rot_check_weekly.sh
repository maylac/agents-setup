#!/bin/zsh
# launchd (com.maylac.selfimprove-rot) から週次で呼ばれるラッパー。
# findings または巡回期限があれば macOS 通知を出し、古いレポートを刈る。
set -u

SELFIMPROVE="$HOME/workspace/agents-setup/selfimprove"
OUT=$(/usr/bin/python3 "$SELFIMPROVE/scripts/rot_check.py" 2>&1)
STATUS=$?
echo "$OUT"

if [ $STATUS -ne 0 ]; then
  SUMMARY=$(echo "$OUT" | grep '^rot_check:' | head -1)
  /usr/bin/osascript -e "display notification \"${SUMMARY} → /self-improve で対応\" with title \"selfimprove 週次チェック\"" 2>/dev/null || true
fi

# レポートは直近8週分だけ残す
ls -t "$SELFIMPROVE"/reports/rot-*.md 2>/dev/null | tail -n +9 | while read -r f; do
  rm -f "$f"
done

exit 0
