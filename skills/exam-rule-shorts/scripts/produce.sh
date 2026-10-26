#!/bin/bash
# usage: tools/produce.sh <content files...>  — merge, synth, build, frame-QA, render missing videos (2 at a time)
set -e
cd "$(dirname "$0")/.."
BATCH="$PWD"
SKILL_DIR="${SKILL_DIR:-$HOME/.agents/skills/exam-rule-shorts}"
python3 tools/lint_content.py "$@"
python3 - "$@" <<'PY'
import json,sys
eps=[e for f in sys.argv[1:] for e in json.load(open(f))]
json.dump(eps,open('content/episodes.json','w'),ensure_ascii=False,indent=1)
print(len(eps),'episodes')
PY
python3 synthesize.py --input content/episodes.json --all --timed-output audio/episodes-timed.json > evidence/synth.log 2>&1
cd production
node render.mjs validate --input ../audio/episodes-timed.json --all 2>&1 | grep -E "error\(s\)" 
node render.mjs build --input ../audio/episodes-timed.json --all > /dev/null 2>&1
IDS=$(python3 -c "import json;print(' '.join(e['id'] for e in json.load(open('../content/episodes.json'))))")
(cd ${PLAYWRIGHT_DIR:-$HOME/workspace/maylac/reskilling-os} && node "$SKILL_DIR/scripts/shorts-frames.cjs" "$BATCH" $IDS) | tee ../evidence/frames.log
grep -q "no layout issues" ../evidence/frames.log || { echo "layout issues: fix before rendering"; exit 1; }
# Render only episodes whose video is missing or older than their content (content hash file)
TODO=$(python3 - <<'PY'
import json,hashlib,os
eps=json.load(open('../content/episodes.json')); out=[]
for e in eps:
    h=hashlib.sha256(json.dumps(e,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    hf=f'../videos/{e["id"]}.hash'
    if not (os.path.exists(f'../videos/{e["id"]}.mp4') and os.path.exists(hf) and open(hf).read()==h): out.append(e['id'])
print(' '.join(out))
PY
)
echo "render: $TODO"
set -- $TODO
half=$(( ($# + 1) / 2 ))
A=$(echo $TODO | tr ' ' '\n' | head -n $half | paste -sd, -); B=$(echo $TODO | tr ' ' '\n' | tail -n +$((half+1)) | paste -sd, -)
[ -n "$A" ] && node render.mjs render --input ../audio/episodes-timed.json --episode $A --keep-going > ../evidence/render-a.log 2>&1 &
[ -n "$B" ] && node render.mjs render --input ../audio/episodes-timed.json --episode $B --keep-going > ../evidence/render-b.log 2>&1 &
wait
python3 - <<'PY'
import json,hashlib,os,subprocess
ff=os.path.realpath('node_modules/ffmpeg-static/ffmpeg')
for e in json.load(open('../content/episodes.json')):
    v=f'../videos/{e["id"]}.mp4'
    if not os.path.exists(v): print('MISSING',e['id']); continue
    r=subprocess.run([ff,'-v','error','-i',v,'-f','null','-'],capture_output=True,text=True)
    if r.stderr.strip(): print('DECODE',e['id'],r.stderr[:200]); continue
    open(f'../videos/{e["id"]}.hash','w').write(hashlib.sha256(json.dumps(e,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
print('videos verified')
PY
