#!/bin/bash
# Full content pipeline for one exam, resumable (each finished step leaves evidence/step-<n>-<exam>).
# usage: tools/pipeline.sh <exam>
cd "$(dirname "$0")/.."
C=~/.claude/skills/cross-harness-collab/scripts/consult.py
ex=$1
log() { echo "$(date +%T) $ex $*" >> evidence/pipeline.log; }
slot() { while :; do
  if mkdir /tmp/codex-slot.lock 2>/dev/null; then
    if [ "$(pgrep -f 'codex exec' | wc -l)" -lt 3 ]; then (sleep 25; rmdir /tmp/codex-slot.lock) & return; fi
    rmdir /tmp/codex-slot.lock
  fi
  sleep 20
done; }
owned="--owned-path content/$ex.json"
case $ex in aws-*) owned="$owned --owned-path evidence/coverage-$ex.json";; esac
work() {  # work <name> <brief file>
  slot; python3 $C --target codex --cwd "$PWD" --mode work $owned --timeout 2400 < "$2" > receipts/$1-$ex.json 2> receipts/$1-$ex.err
}
lintfix() {  # keep the file passing the linter
  for i in 1 2; do
    out=$(python3 tools/lint_content.py content/$ex.json) && return 0
    printf 'Goal: make content/%s.json pass the linter without changing facts. You own ONLY content/%s.json.\nLinter output:\n%s\nRewrite only the flagged fields (keep meaning, ids, task, icons rules). Acceptance: python3 tools/lint_content.py content/%s.json -> "content ok". Reply in <= 5 lines.\n' "$ex" "$ex" "$out" "$ex" > briefs/lintfix-$ex.txt
    work lintfix$i briefs/lintfix-$ex.txt
  done
  python3 tools/lint_content.py content/$ex.json > /dev/null
}
consult() {  # consult <name> <brief> <evidence out> [model]
  for i in 1 2 3; do
    slot; python3 $C --target codex --cwd "$PWD" --mode consult ${4:+--model $4} --effort ${5:-medium} --timeout 1800 < "$2" > receipts/$1-$ex.json 2> receipts/$1-$ex.err
    python3 - "receipts/$1-$ex.json" "$3" <<'PY' && return 0
import json,sys
d=json.load(open(sys.argv[1]))
if d.get('status')!='success': sys.exit(1)
s=d.get('result') or ''
a=json.loads(s[s.index('['):s.rindex(']')+1])
json.dump(a,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
PY
    sleep 90
  done
  return 1
}
step() { [ -f evidence/step-$1-$ex ]; }
done_step() { touch evidence/step-$1-$ex; log "step $1 done"; }

step 1 || { work write briefs/write-$ex.txt; lintfix || { log "write lint failed"; exit 1; }; done_step 1; }
step cov || {
  for i in 1 2; do
    gap=$(python3 tools/check_coverage.py $ex 2>&1) && break
    printf 'Goal: close the coverage gap in content/%s.json. You own ONLY %s.\nCoverage check output:\n%s\nFollow briefs/write-%s.txt exactly (sources, schema, style, icons, terminology). Add one new episode for each missing task (or to meet each short domain quota), continuing the id numbering; update evidence/coverage-%s.json if it exists. Do not change existing episodes. Acceptance: python3 tools/lint_content.py content/%s.json -> "content ok" and python3 tools/check_coverage.py %s exits 0. Reply in <= 6 lines.\n' "$ex" "content/$ex.json (and evidence/coverage-$ex.json if present)" "$gap" "$ex" "$ex" "$ex" "$ex" > briefs/gap-$ex.txt
    work gap$i briefs/gap-$ex.txt
    lintfix || { log "gap lint failed"; exit 1; }
  done
  python3 tools/check_coverage.py $ex > evidence/coverage-check-$ex.txt 2>&1 || { log "coverage still short: $(tail -2 evidence/coverage-check-$ex.txt)"; exit 1; }
  done_step cov; }
step 2 || { consult audit1 briefs/audit-$ex.txt evidence/audit1-$ex.json || { log "audit1 failed"; exit 1; }
            sed "s#{AUDIT}#evidence/audit1-$ex.json#" briefs/fix-$ex.txt > briefs/fix1-$ex.txt; work fix1 briefs/fix1-$ex.txt; lintfix && done_step 2 || exit 1; }
step 3 || { work diagram briefs/diagram-$ex.txt; lintfix && done_step 3 || exit 1; }
step 4 || { sed 's/^Read-only fact audit of/Final read-only fact and icon audit (earlier audits were applied) of/' briefs/audit-$ex.txt > briefs/audit2-$ex.txt
            consult audit2 briefs/audit2-$ex.txt evidence/audit2-$ex.json || { log "audit2 failed"; exit 1; }
            sed "s#{AUDIT}#evidence/audit2-$ex.json#" briefs/fix-$ex.txt > briefs/fix2-$ex.txt; work fix2 briefs/fix2-$ex.txt; lintfix && done_step 4 || exit 1; }
for r in 1 2 3 4; do
  step term$r && continue
  sed "s/{N}/$r/" briefs/term-audit-$ex.txt > briefs/term-audit$r-$ex.txt
  consult term$r briefs/term-audit$r-$ex.txt evidence/term$r-$ex.json gpt-6-luna high || { log "term$r audit failed"; exit 1; }
  if [ "$(python3 -c "import json;print(len(json.load(open('evidence/term$r-$ex.json'))))")" != 0 ]; then
    cat > briefs/term-fix$r-$ex.txt <<BRIEF
Goal: apply the Japanese terminology audit evidence/term$r-$ex.json to content/$ex.json. You own ONLY content/$ex.json.
Replace each "current" with "fix" (or a better official-term wording if the fix breaks a width limit). Apply the same correction everywhere the same wrong term appears in the file, including narration, captions and node labels. Use the vendor's official Japanese terminology (AWS: docs.aws.amazon.com/ja_jp, AWS account = アカウント, never 口座; Anthropic: platform.claude.com/docs/ja).
Keep ids, task, scene structure, facts, icons and edges unchanged; narration still ends 「のだ。」.
Acceptance: python3 tools/lint_content.py content/$ex.json → "content ok". Reply in <= 6 lines.
BRIEF
    work termfix$r briefs/term-fix$r-$ex.txt
  fi
  lintfix && done_step term$r || exit 1
done
python3 tools/check_coverage.py $ex > evidence/coverage-check-$ex.txt 2>&1 && touch evidence/READY-$ex && log READY || log "coverage gap: $(cat evidence/coverage-check-$ex.txt | tail -3)"
