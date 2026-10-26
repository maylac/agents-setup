---
name: exam-rule-shorts
description: Produce Japanese vertical (1080×1920) ~40 s "鉄則ショート" videos that teach one certification-exam decision rule each — dark graphite look, large unboxed official AWS Architecture Icons, VOICEVOX ずんだもん narration — for any exam with a Vantik field manual and flashcard deck. Use for 「鉄則をショート動画に」「試験ごとのショート動画」「公式アイコン付きの解説動画」. For wrong-answer review clips use vantik-weakness-shorts instead.
---

# Exam rule shorts

Approved by the user on 2026-10-26 after an SAP-C02 pilot (`scripts/example-episodes.json`).
The look is fixed: dark graphite background (no neon, no glow, no cyberpunk), official icons at
156–210 px with **no box around them**, label and short sub-line under each icon, thin grey
arrows, muted accent pills. Do not reintroduce bordered cards, drop shadows or a light theme.

## Pieces

| Piece | Path (this skill) | Notes |
|---|---|---|
| Renderer (HyperFrames + GSAP) | `renderer/` | Copy to `<batch>/production/`; link `node_modules` from a checkout that already has `hyperframes`, `gsap`, `ffmpeg-static`, `@ffprobe-installer/ffprobe` (e.g. `~/tasks/vantik-sap-video-20261018/production/node_modules`) or `npm install`. Nodes name icons directly: `"icon": "Arch_Amazon-DynamoDB_64"`; `_Light` general icons switch to the official `_Dark` variant automatically. |
| Content linter | `scripts/lint_content.py` | Copy to `<batch>/tools/`. Enforces one-line titles (≤ 11 wide), labels ≤ 8, subs ≤ 12, body 2×21, narration 45–95 chars ending 「のだ。」, an official icon on every node, official doc URLs, no exam-tactic wording. |
| VOICEVOX synth | `scripts/synthesize.py` | Copy to `<batch>/`. Needs VOICEVOX running (`curl 127.0.0.1:50021/version`). |
| Frame QA | `scripts/shorts-frames.cjs` | Run from a directory where `require('playwright')` resolves (reskilling-os). Screenshots every scene at +7.5 s and reports label wraps, overflow, text touching the diagram, verdict touching captions. |
| Worker brief | `scripts/brief-template.txt` | One exam per worker (`{EXAM} {LABEL} {PREFIX} {GUIDES} {FLASHCARDS} {IDNOTE} {EXTRA}`, absolute paths). |
| Icon provenance | `scripts/icon-package-source.json` | Official package URL + SHA-256. Extract `Architecture-Service-Icons_*/*/64/*.svg`, `Resource-Icons_*/*/*_48.svg`, `Resource-Icons_*/Res_General-Icons/Res_48_{Light,Dark}/*.svg`, `Architecture-Group-Icons_*/*.svg` into `<batch>/assets/icons/`, then `ls assets/icons > assets/ICON_INDEX.txt`. Check https://aws.amazon.com/architecture/icons/ for a newer release first. |

## Procedure

1. **Batch dir** `~/tasks/rule-shorts-<YYYYMMDD>/` with `content/ audio/ videos/ evidence/ assets/icons/ tools/ briefs/ receipts/`.
2. **Content (Codex workers, one exam each).** Sources are only the exam's Vantik field manual(s)
   (`vantik-content/exam_guides/`) and audited flashcards (`vantik-content/flashcards/<exam>.json`);
   every scene's `source_url` comes from them. Dispatch with `cross-harness-collab`
   `--mode work --owned-path content/<exam>.json --timeout 2400`, ~5 in parallel. Scenes:
   場面 → 罠 (wrong) → 鉄則 (rule) → 確認 (question + answer). 12 episodes per exam.
3. **Lint + audit.** `python3 tools/lint_content.py content/<exam>.json` must print `content ok`.
   Then an independent fact audit (Codex `--mode consult` or a Claude reviewer) against the cited
   pages; fix or drop any claim not stated in the source. Wrong icons on generic boxes count as defects.
4. **Audio.** Merge the approved exams into `content/episodes.json`, then
   `python3 synthesize.py --input content/episodes.json --all --timed-output audio/episodes-timed.json`.
   The renderer only merges diagrams from `content/episodes.json` when the timed file is named
   `episodes-timed.json`.
5. **Build + frame QA.** `node render.mjs build --input ../audio/episodes-timed.json --all`, then
   `node shorts-frames.cjs <batch> <ids…>` → must print `no layout issues`; look at a 4-scene contact
   sheet per exam (`ffmpeg -i <id>-s%d.png -vf scale=360:-1,tile=4x1`).
6. **Render** `node render.mjs render --input ../audio/episodes-timed.json --episode a,b,c --keep-going`
   in groups; `ffmpeg -v error -i x.mp4 -f null -` must be silent for every file.
7. **Deliver** to the learner's iCloud `Vantik/<EXAM>/<date>-rule-shorts/`. Publishing to the NAS
   library / Vantik review-videos feed is a production write: follow `vantik-weakness-shorts` step 6
   and only with the user's explicit OK.
8. **Report** (Japanese): clips per exam, total minutes, lint/audit/QA results, what was not published.

## Known failure modes

- A long English service name wraps mid-word ("Organization/s") without overflowing — the frame QA
  checks label height, not only overflow; shorten the label.
- Two-line scene titles push the body into the diagram; keep titles ≤ 11 wide.
- Both directions of a two-way edge labelled → labels overlap; label one direction only.
- Line-style general icons are black: use the `_Light` name so the renderer picks the `_Dark` file.
- Workers given several exams at once give up or pad; one exam per worker.
- Claude-certification exams have no official icon set; do not dress them in AWS service icons.
