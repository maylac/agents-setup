#!/bin/bash
# One official-terminology round for one exam: audit (Luna, read-only) -> fix (Luna) -> lint.
# usage: ROUND=1 tools/term_round.sh <exam> [content files...]   (run ROUND=1..4)
# Needs briefs/term-audit-<exam>.txt filled from term-audit-brief-template.txt ({FILES} {EXAM}; {N} is the round).
cd "$(dirname "$0")/.."
C=~/.claude/skills/cross-harness-collab/scripts/consult.py
ROUND=${ROUND:-1}
ex=$1; shift
files=${*:-content/$ex.json}
owned=""; for f in $files; do owned="$owned --owned-path $f"; done
# A short-lived lock so several waiting jobs cannot all see a free slot at once (Codex 429s above ~3).
slot() { while :; do
  if mkdir /tmp/codex-slot.lock 2>/dev/null; then
    if [ "$(pgrep -f 'codex exec' | wc -l)" -lt 3 ]; then (sleep 25; rmdir /tmp/codex-slot.lock) & return; fi
    rmdir /tmp/codex-slot.lock
  fi
  sleep 20
done; }
sed "s/{N}/$ROUND/" briefs/term-audit-$ex.txt > briefs/term-audit$ROUND-$ex.txt
for i in 1 2 3 4; do
  slot; python3 $C --target codex --cwd "$PWD" --mode consult --model gpt-6-luna --effort high --timeout 1800 < briefs/term-audit$ROUND-$ex.txt > receipts/term$ROUND-$ex.json 2> receipts/term$ROUND-$ex.err
  python3 - "$ex" "$ROUND" <<'PY' && break
import json,sys
ex,r=sys.argv[1:]; d=json.load(open(f'receipts/term{r}-{ex}.json'))
if d.get('status')!='success': sys.exit(1)
s=d['result']; a=json.loads(s[s.index('['):s.rindex(']')+1])
json.dump(a,open(f'evidence/term{r}-{ex}.json','w'),ensure_ascii=False,indent=1); print(ex,'round',r,len(a))
PY
  sleep 120
done
cat > briefs/term-fix$ROUND-$ex.txt <<BRIEF
Goal: apply the Japanese terminology audit evidence/term$ROUND-$ex.json to $files. You own ONLY: $files.
Replace each "current" with "fix" (or a better official-term wording if the fix breaks a width limit). Apply the same correction everywhere the same wrong term appears in your files, including narration, captions and node labels. Use the vendor's official Japanese terminology (AWS: docs.aws.amazon.com/ja_jp; AWS account = アカウント, never 口座).
Keep ids, scene structure, facts, icons and edges unchanged; narration still ends 「のだ。」.
Acceptance: python3 tools/lint_content.py $files → "content ok". Reply in <= 6 lines.
BRIEF
slot; python3 $C --target codex --cwd "$PWD" --mode work $owned --timeout 1800 < briefs/term-fix$ROUND-$ex.txt > receipts/term-fix$ROUND-$ex.json 2> receipts/term-fix$ROUND-$ex.err
python3 tools/lint_content.py $files && touch evidence/TERM$ROUND-READY-$ex && echo "$ex round $ROUND done"
