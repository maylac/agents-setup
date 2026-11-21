#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -r "$TMP"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

HOOK="$ROOT/agents/hooks/notify-mobile.sh"
mkdir -p "$TMP/bin" "$TMP/home" "$TMP/no-transport-home"
cat >"$TMP/bin/curl" <<'SH'
#!/bin/sh
printf '%s\n' "$*" >>"$HOME/curl-calls.log"
exit 0
SH
chmod +x "$TMP/bin/curl"
printf '%s\n' 'NOTIFY_NTFY_URL=fixture://sink' >"$TMP/notify.env"

for kind in approval done idle note; do
  case "$kind" in
    note) args=(note Fixture "sample note") ;;
    *) args=("$kind" Fixture) ;;
  esac
  printf '{}' | HOME="$TMP/home" AGENTS_NOTIFY_ENV="$TMP/notify.env" PATH="$TMP/bin:$PATH" \
    "$HOOK" "${args[@]}" || fail "hook failed for $kind"
done
grep -Fq 'Fixture が承認待ち' "$TMP/home/curl-calls.log" || fail 'approval message changed'
grep -Fq 'Fixture が完了' "$TMP/home/curl-calls.log" || fail 'done message changed'
grep -Fq 'Fixture が入力待ち' "$TMP/home/curl-calls.log" || fail 'idle message changed'
grep -Fq 'sample note' "$TMP/home/curl-calls.log" || fail 'note message missing'

printf '{}' | HOME="$TMP/no-transport-home" AGENTS_NOTIFY_ENV="$TMP/not-configured" PATH="$TMP/bin:$PATH" \
  "$HOOK" note Fixture "private payload" || fail 'no-transport hook failed'
grep -Fq 'not sent (no transport configured) kind=note' "$TMP/no-transport-home/.local/state/agents-notify/notify.log" \
  || fail 'no-transport logging missing'
grep -Fq 'private payload' "$TMP/no-transport-home/.local/state/agents-notify/notify.log" \
  && fail 'message leaked into notification log'
[ ! -e "$TMP/no-transport-home/curl-calls.log" ] || fail 'no-transport run invoked curl'

PROJECT=$(basename "$PWD")
for kind in approval done idle; do
  printf '{}' | HOME="$TMP/no-transport-home" AGENTS_NOTIFY_ENV="$TMP/not-configured" PATH="$TMP/bin:$PATH" \
    "$HOOK" "$kind" Fixture || fail "no-transport hook failed for $kind"
done
grep -Fq "not sent (no transport configured) kind=approval: [$PROJECT] Fixture が承認待ち: tool" \
  "$TMP/no-transport-home/.local/state/agents-notify/notify.log" || fail 'no-transport approval message changed'
grep -Fq "not sent (no transport configured) kind=done: [$PROJECT] Fixture が完了" \
  "$TMP/no-transport-home/.local/state/agents-notify/notify.log" || fail 'no-transport done message changed'
grep -Fq "not sent (no transport configured) kind=idle: [$PROJECT] Fixture が入力待ち" \
  "$TMP/no-transport-home/.local/state/agents-notify/notify.log" || fail 'no-transport idle message changed'

FIXTURE="$TMP/repo"
REPORTS="$FIXTURE/selfimprove/reports"
mkdir -p "$REPORTS" "$FIXTURE/selfimprove/scripts" "$FIXTURE/agents/hooks" "$TMP/weekly-home"
cp "$ROOT/selfimprove/scripts/rot_check_weekly.sh" "$FIXTURE/selfimprove/scripts/rot_check_weekly.sh"
cat >"$FIXTURE/selfimprove/scripts/rot_check.py" <<'PY'
import argparse
import datetime as dt
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("--report-dir", required=True)
args = parser.parse_args()
today = dt.date.today()
text = f"""# rot check {today.isoformat()}

- findings: 1 / due sources: 1

## Findings (要対応)
- [WARN][fixture] stable warning

## 巡回期限が来た蒸留元 (③ /self-improve sources)
- source-a (期限{(today - dt.date(2026, 1, 1)).days}日超過)

## Info (参考)
- [memory] fixture: {(today - dt.date(2026, 1, 1)).days}日未更新
"""
path = pathlib.Path(args.report_dir) / f"rot-{today.isoformat()}.md"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(text, encoding="utf-8")
print("rot_check: findings=1 due_sources=1")
raise SystemExit(0)
PY
cat >"$FIXTURE/agents/hooks/notify-mobile.sh" <<'SH'
#!/bin/sh
printf '%s\n' "$*" >>"$HOME/weekly-notification.log"
SH
chmod +x "$FIXTURE/agents/hooks/notify-mobile.sh"
python3 - "$REPORTS" <<'PY'
import datetime as dt
import pathlib
import sys

reports = pathlib.Path(sys.argv[1])
today = dt.date.today()
for weeks_ago in (1, 2, 3):
    day = today - dt.timedelta(days=7 * weeks_ago)
    warning = "stable warning" if weeks_ago < 3 else "changed warning"
    text = f"""# rot check {day.isoformat()}

- findings: 1 / due sources: 1

## Findings (要対応)
- [WARN][fixture] {warning}

## 巡回期限が来た蒸留元 (③ /self-improve sources)
- source-a (期限{10 + weeks_ago}日超過)

## Info (参考)
- [memory] fixture: {20 + weeks_ago}日未更新
"""
    (reports / f"rot-{day.isoformat()}.md").write_text(text, encoding="utf-8")
PY
WEEKLY_SHELL=/bin/sh
if [ "$(uname -s)" = Darwin ]; then WEEKLY_SHELL=/bin/zsh; fi
HOME="$TMP/weekly-home" "$WEEKLY_SHELL" "$FIXTURE/selfimprove/scripts/rot_check_weekly.sh" >"$TMP/weekly.stdout" \
  || fail 'weekly wrapper failed'
grep -Fq 'note selfimprove rot週次: WARN 1件、期限超過 1件、同内容 3週連続' "$TMP/weekly-home/weekly-notification.log" \
  || fail 'weekly summary was not sent through the repo-local hook path'
grep -Fxq 'rot週次: WARN 1件、期限超過 1件、同内容 3週連続' "$TMP/weekly.stdout" \
  || fail 'weekly summary was not available in local stdout'

printf 'PASS: note modes, no-transport logging, and weekly continuity fixture\n'
