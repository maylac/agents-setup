#!/bin/bash
# Final terminology round: audit 3 (Luna) -> fix -> lint. Waits for a free Codex slot (max 3).
cd "$(dirname "$0")/.."
C=~/.claude/skills/cross-harness-collab/scripts/consult.py
ROUND=${ROUND:-1}
ex=$1; files="content/$ex.json"; [ "$ex" = aws-sap-c02 ] && files="content/pilot.json content/aws-sap-c02.json"
owned=""; for f in $files; do owned="$owned --owned-path $f"; done
# A short-lived lock so several waiting jobs cannot all see a free slot at once.
slot() { while :; do
  if mkdir /tmp/codex-slot.lock 2>/dev/null; then
    if [ "$(pgrep -f 'codex exec' | wc -l)" -lt 3 ]; then (sleep 25; rmdir /tmp/codex-slot.lock) & return; fi
    rmdir /tmp/codex-slot.lock
  fi
  sleep 20
done; }
for i in 1 2 3 4; do
  slot; python3 $C --target codex --cwd "$PWD" --mode consult --model gpt-6-luna --effort high --timeout 1800 < briefs/term-audit-$ex.txt > receipts/term${ROUND}-$ex.json 2> receipts/term${ROUND}-$ex.err
  python3 - "$ex" <<'PY' && break
import json,sys
ex=sys.argv[1]; d=json.load(open(f'receipts/term${ROUND}-{ex}.json'))
if d.get('status')!='success': sys.exit(1)
s=d['result']; a=json.loads(s[s.index('['):s.rindex(']')+1])
json.dump(a,open(f'evidence/term${ROUND}-{ex}.json','w'),ensure_ascii=False,indent=1); print(ex,'round ${ROUND}',len(a))
PY
  sleep 120
done
sed "s#evidence/term2-$ex.json#evidence/term${ROUND}-$ex.json#" briefs/term-fix2-$ex.txt > briefs/term-fix3-$ex.txt 2>/dev/null || sed "s#evidence/term1-$ex.json#evidence/term${ROUND}-$ex.json#" briefs/term-fix1-$ex.txt > briefs/term-fix3-$ex.txt
grep -q term${ROUND} briefs/term-fix3-$ex.txt || sed "s#evidence/term1-$ex.json#evidence/term${ROUND}-$ex.json#" briefs/term-fix1-$ex.txt > briefs/term-fix3-$ex.txt
slot; python3 $C --target codex --cwd "$PWD" --mode work $owned --timeout 1800 < briefs/term-fix3-$ex.txt > receipts/term-fix3-$ex.json 2> receipts/term-fix3-$ex.err
python3 tools/lint_content.py $files && touch evidence/TERM${ROUND}-READY-$ex && echo "$ex round ${ROUND} done"
