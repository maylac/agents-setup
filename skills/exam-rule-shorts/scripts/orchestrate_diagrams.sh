#!/bin/bash
# For each exam: wait for its fix (and audit2 when one was started), then run the diagram pass,
# then a final fact+icon audit. Receipts land in receipts/.
cd "$(dirname "$0")/.."
C=~/.claude/skills/cross-harness-collab/scripts/consult.py
G=${VANTIK_CONTENT:-$HOME/workspace/maylac/vantik-content}/exam_guides
run_exam() {
  ex=$1
  until [ -s receipts/fix-$ex.json ]; do sleep 20; done
  audit=""
  if [ -f briefs/audit2-$ex.txt ]; then
    until [ -s receipts/audit2-$ex.json ]; do sleep 20; done
    if python3 - "$ex" <<'PY'
import json,sys
ex=sys.argv[1]; d=json.load(open(f'receipts/audit2-{ex}.json'))
r=d.get('result') or ''
a=json.loads(r[r.index('['):r.rindex(']')+1]) if d.get('status')=='success' and '[' in r else []
json.dump(a,open(f'evidence/audit2-{ex}.json','w'),ensure_ascii=False,indent=1)
sys.exit(0 if a else 1)
PY
    then audit=" Also resolve every defect in evidence/audit2-$ex.json (a second independent fact audit; node indexes 0-based) using only the exam sources: the field manual(s) under $G for $ex and ${VANTIK_CONTENT:-$HOME/workspace/maylac/vantik-content}/flashcards/$ex.json."; fi
  fi
  sed -e "s#{EXAM}#$ex#g" -e "s#{AUDIT}#$audit#" briefs/diagram-template.txt > briefs/diagram-$ex.txt
  python3 $C --target codex --cwd "$PWD" --mode work --owned-path content/$ex.json --timeout 2400 < briefs/diagram-$ex.txt > receipts/diagram-$ex.json 2> receipts/diagram-$ex.err
  sed 's/^Read-only fact audit of/Final read-only fact and icon audit (earlier audits were applied) of/' briefs/audit-$ex.txt > briefs/audit3-$ex.txt
  python3 $C --target codex --cwd "$PWD" --mode consult --effort medium --timeout 1200 < briefs/audit3-$ex.txt > receipts/audit3-$ex.json 2> receipts/audit3-$ex.err
  echo "$ex done $(date +%T)"
}
for ex in "$@"; do run_exam $ex & sleep 2; done
wait
