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
   every scene's `source_url` comes from them. Fill `scripts/brief-template.txt` per exam and dispatch
   with `cross-harness-collab` `--mode work --owned-path content/<exam>.json --timeout 2400`, ~5 in
   parallel (they finish in 3–6 min). Scenes: 場面 → 罠 (wrong) → 鉄則 (rule) → 確認. 12 episodes per exam.
3. **Audit → fix → diagram pass → final audit (all Codex).** Copy `scripts/{audit,fix,diagram}-brief-template.txt`
   to `briefs/{audit,fix,diagram}-template.txt` (fill `{GUIDES}`/`{GUIDE_DIR}`/`{FLASHCARDS}`).
   - Audit: `--mode consult --effort medium --timeout 1200`; it returns a JSON defect list → `evidence/audit-<exam>.json`.
     First audits found 4–65 defects per exam, mostly service icons on generic boxes, plus "罠" that were
     actually valid and rules that dropped boundary conditions. Always run it.
   - Fix: `--mode work` with the fix brief.
   - Diagram pass: first drafts reuse one diagram for all scenes ("アプリ → DAX 連携" ×4). The diagram
     brief requires s1 situation / s2 the wrong design / s3 the correct flow (3 nodes when 3 components) /
     s4 問い→答え, and edge labels that name what flows. `scripts/orchestrate_diagrams.sh <exams…>`
     chains diagram pass + final audit per exam once each fix receipt exists.
   - The linter must print `content ok` after every step; it rejects identical diagrams in s1–s3 and vague edge labels.
   - `scripts/finish_exam.sh <exam>` waits for the final audit, reruns it once if Codex exited on MCP
     auth noise, applies the remaining defects (usually 1–9) and touches `evidence/READY-<exam>`.
   - **Official Japanese terminology (mandatory before audio).** The user caught 「口座」 for AWS
     account in published clips (2026-10-26). Run `scripts/term_round.sh <exam>` with `ROUND=1..4`
     (audit with `scripts/term-audit-brief-template.txt` → fix → lint). Rounds kept finding new real
     defects (口座, 鍵→キー, CWエージェント, 指標→メトリクス, partition, 閾値→しきい値, 待機系→スタンバイ,
     呼出→呼び出し, IAM IC); run at least 4 rounds, then grep the usual literal terms yourself.
     The linter bans known mistranslations (`MISTRANSLATED`) and allows node labels up to 10 wide so
     official names fit. Codex returns 429 above ~3 concurrent jobs and Astra may be rate-limited:
     the script uses a slot lock (max 3) and `gpt-6-luna` for audits.
4. **Produce in one go:** copy `scripts/produce.sh` to `<batch>/tools/` and run it with every READY
   content file (plus earlier exams). It lints, merges into `content/episodes.json`, synthesizes,
   builds, runs frame QA (stops on any issue), renders only episodes whose content hash changed
   (2 renders in parallel; a "render_cancelled" failure is transient — rerun picks it up) and
   decode-checks every MP4. Steps 5–6 below are what it does.
5. **Audio.** Merge the approved exams into `content/episodes.json`, then
   `python3 synthesize.py --input content/episodes.json --all --timed-output audio/episodes-timed.json`.
   The renderer only merges diagrams from `content/episodes.json` when the timed file is named
   `episodes-timed.json`.
6. **Build + frame QA.** `node render.mjs build --input ../audio/episodes-timed.json --all`, then
   `node shorts-frames.cjs <batch> <ids…>` → must print `no layout issues`; look at a 4-scene contact
   sheet per exam (`ffmpeg -i <id>-s%d.png -vf scale=360:-1,tile=4x1`).
7. **Render** `node render.mjs render --input ../audio/episodes-timed.json --episode a,b,c --keep-going`
   in groups; `ffmpeg -v error -i x.mp4 -f null -` must be silent for every file.
8. **Deliver + publish** (publishing needs the user's explicit OK; it was given on 2026-10-26).
   - iCloud: `Vantik/<EXAM>/<date>-rule-shorts/<id>_<title>.mp4`.
   - Video library: `curl <origin>/catalog.json > evidence/live-catalog.json`, then
     `VIDEO_LIBRARY_ORIGIN=<origin> python3 tools/build_library_package.py --live-catalog evidence/live-catalog.json`
     → `package/dist` (content-addressed media/posters/captions + merged catalog, one collection
     `<exam>-rules-<date>` per exam, poster = rule scene) and `package/rule-shorts-manifest.json`.
     On the NAS (`/volume1/docker/vantik-video-library`): check `readlink current` and the live catalog
     sha, `cp -al releases/<current> releases/<new>`, `rm` the hard-linked `dist/catalog.json`, tar-stream
     `package/dist` in, `sha256sum -c` every asset, `ln -sfn` + `mv -T` to switch `current`, then
     `cd current/deploy && docker compose -p vantik-video-library up -d --force-recreate video-library`
     (without `-p` compose picks project "deploy" and fails on the container name). Smoke: catalog sha,
     Range 206 on a new mp4, 200 `text/vtt`, an old asset still 200. Rollback = switch `current` back.
   - Vantik: copy the manifest to `vantik-content/rule_shorts/manifest.json` with `chapters` emptied
     (chapter chips cover the burned-in captions), `python3 tools/validate.py`, commit, push,
     `bash tools/sync-to-nas.sh`. The app lists them under 復習 → 鉄則ショート for the selected exam
     (`GET /api/rule-shorts?exam_code=`), separate from 動画で復習 because they are input, not review.
9. **Report** (Japanese): clips per exam, total minutes, lint/audit/QA results, what was not published.

## Known failure modes

- A long English service name wraps mid-word ("Organization/s") without overflowing — the frame QA
  checks label height, not only overflow; shorten the label.
- Two-line scene titles push the body into the diagram; keep titles ≤ 11 wide.
- Both directions of a two-way edge labelled → labels overlap; label one direction only.
- Line-style general icons are black: use the `_Light` name so the renderer picks the `_Dark` file.
- Workers given several exams at once give up or pad; one exam per worker.
- Requiring an icon on every node pushes writers to put service icons on concepts ("学習データ" with the
  SageMaker icon). Generic concepts take the general `_Light` icons; the audit checks this.
- Titles of exactly 11 full-width characters wrapped at 88 px, and Latin-heavy titles
  ("CodeDeployで段階展開") wrapped even after shrinking; the renderer budgets 0.8 em per capital and
  0.64 em per lowercase letter. Frame QA flags any remaining title wrap.
- Codex consult runs can exit 1 on unrelated MCP auth noise; rerun the same brief.
- Claude-certification exams have no official icon set; do not dress them in AWS service icons.
