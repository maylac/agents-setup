#!/bin/bash
# After orchestrate_diagrams wrote receipts/audit3-<exam>.json: rerun a failed audit once, then fix its defects.
cd "$(dirname "$0")/.."
C=~/.claude/skills/cross-harness-collab/scripts/consult.py
ex=$1
until [ -s receipts/audit3-$ex.json ]; do sleep 30; done
extract() { python3 - "$ex" <<'PY'
import json,sys
ex=sys.argv[1]; d=json.load(open(f'receipts/audit3-{ex}.json')); r=d.get('result') or ''
if d.get('status')!='success': sys.exit(2)
a=json.loads(r[r.index('['):r.rindex(']')+1]); json.dump(a,open(f'evidence/audit3-{ex}.json','w'),ensure_ascii=False,indent=1); print(ex,'audit3',len(a))
PY
}
extract || { python3 $C --target codex --cwd "$PWD" --mode consult --effort medium --timeout 1200 < briefs/audit3-$ex.txt > receipts/audit3-$ex.json 2> receipts/audit3-$ex.err; extract || { echo "$ex audit3 failed twice"; exit 1; }; }
sed "s#evidence/audit-$ex.json#evidence/audit3-$ex.json#" briefs/fix-$ex.txt > briefs/fix3-$ex.txt
python3 $C --target codex --cwd "$PWD" --mode work --owned-path content/$ex.json --timeout 1800 < briefs/fix3-$ex.txt > receipts/fix3-$ex.json 2> receipts/fix3-$ex.err
python3 tools/lint_content.py content/$ex.json && touch evidence/READY-$ex
