---
name: vantik-weakness-shorts
description: Turn a learner's Vantik wrong-answer history into a batch of Japanese vertical (1080×1920) explainer shorts voiced by VOICEVOX ずんだもん with animated box-and-arrow diagrams, then publish them to the private NAS video library and Vantik's review-videos feed. Source map + batch procedure + known failure modes for 「誤答を潰すショート動画を大量に作って」「弱点解説の縦型動画」「復習動画を増やして」.
---

# Vantik weakness shorts

Done three times for SAP-C02 (38 clips 10/18, 60+60 clips 10/23-24). The renderer,
synthesizer, QA and publish tools already exist; this skill is the map so a new batch
starts from them instead of rewriting. Read `~/tasks/learnings/2026-10-18-video-copy-truncation.md`
and `~/tasks/learnings/2026-10-24-concat-tempfile-collision.md` before producing.

## Existing pieces (do not re-implement)

| Piece | Where | Notes |
|---|---|---|
| Renderer (HyperFrames + GSAP, 1080×1920 H.264/AAC) | `~/tasks/vantik-sap-video-20261018/production/` (`render.mjs`, `lib/`, `template/`, `scripts/check-layout.mjs`) | Project-local `node_modules`; later batches symlink to it. `npm run doctor` shows ffmpeg/ffprobe/Chrome. |
| VOICEVOX synthesizer (stdlib Python) | `~/tasks/vantik-sap-video-20261018/synthesize.py` (copied per batch) | Needs `/Applications/VOICEVOX.app` running → engine on `127.0.0.1:50021`, speaker ずんだもん／ノーマル. Reuses WAVs by text+settings hash; `--timed-output` writes the timed JSON the renderer consumes. Pronunciation substitutions are speech-only. |
| Delivery QA (gallery, VTT subtitles, ffprobe + full decode) | `qa_delivery.py` next to the batch | Writes `delivery/qa.json`, `delivery/index.html`. |
| Library packaging / NAS release / manifest publish | `~/tasks/sap-c02-final-20261024/nas-publish/` (`package/`, `deployment/`, `integration/publish_manifest.py`, `publish_cleanup.py`, `vantik-live-qa.cjs`) | Library contract: `~/workspace/maylac/heygen-video-library/library/CONTRACT.md`; Vantik side: reskilling-os `docs/review-videos.md`, `scripts/build_review_video_manifest.py`. |
| Content schema | `content/episodes.json` of either batch | `id, title, scenes[4]{id,kicker,title,body,caption,narration,nodes[2-4]{label,sub},edges{from,to,label},rule?,wrong?,source_url}`, plus `question_ids, attempt_ids, priority, topic, sources[], quiz{question,answer}, verification_status`. `coverage.json` maps episode → question/attempt IDs. |

## Batch procedure

Work in a new dated folder `~/tasks/<exam>-shorts-<YYYYMMDD>/` with `content/ audio/
production/ videos/ delivery/ evidence/ nas-publish/`. Split ownership the way the
last batch did (content / audio+production / delivery+publish), one owner per folder.

1. **Evidence.** Snapshot the production DB with `vantik-prod-verify` (record SHA-256
   and counts). Latest result per `question_id`, repeated misses first, recent misses
   second. Write `evidence/priority-evidence.json` (top N with IDs) and
   `content/weakness-analysis.md` (domain miss rates = practice history, not a score forecast).
2. **Content.** 4 scenes per clip, 50-85 Japanese characters narration per scene,
   30-60 s total: discriminating condition → misconception → correct architecture/reason
   → one retrieval question with the answer. Group several misses into one transferable
   decision rule; never recite copyrighted stems or stored answer letters. `title` ≤ 18
   chars, `body` ≤ 2 lines/70 chars, node label ≤ 13 chars. Rewrite to fit; **never
   slice strings**. Official AWS/vendor URL per scene; stored keys that look wrong get
   `verification_status: needs_review` and a hedged narration. Freeze tranches
   (`BATCH1_READY`, `ALL_READY` markers) so audio/render can start on the first 20.
3. **Audio.** `python3 synthesize.py --input <frozen>.json --all --timed-output audio/<batch>-timed.json`
   (one timed file per frozen input). Check `audio/metadata.json` and a sample WAV.
4. **Render.** `node render.mjs validate|lint --input audio/<batch>-timed.json --all`,
   then `render --episode e01,e02,e03 --keep-going` in small groups (resumable), then
   `node scripts/check-layout.mjs --input …` (real DOM bounds at +2 s per scene, after
   fonts load). Fix text, re-render only changed IDs (hash reuse keeps audio).
5. **Concat + QA.** Run concatenations **sequentially** (shared `concat-<ms>.txt`
   collides when parallel) and compare each output duration to the sum of inputs.
   `python3 qa_delivery.py --timed-input … --build-gallery --build-subtitles --verify`.
   Look at representative frames at scene transitions.
6. **Publish (needs the user's explicit OK for NAS/Vantik writes).** Build a
   content-addressed overlay (`media/<sha>.mp4`, `posters/`, `captions/`) + merged
   `catalog.json` that keeps old entries byte-identical; new collection id
   `<exam>-<YYYYMMDD>[-variant]`, clip ids `<collection>-e01…`, `kind: clip|full`,
   `question_number: null` for concept clips, `question_ids` from `coverage.json`,
   `exam_codes`. Copy to a new release dir on the NAS, switch, verify HTTPS HEADs and
   catalog SHA. Then generate `review-videos.json` with the trusted HTTPS origin, back up
   the live manifest in the container, atomically replace, and QA the Vantik API and
   the review feed on 320/375/414 widths.
7. **Report** (Japanese, short): clip count, watch order (priority 20 first), total
   minutes, evidence snapshot date, needs_review count, library/Vantik verification
   lines, and what was *not* changed (attempt history, answer keys).

## Known failure modes

- Character-count checks pass while meaning is cut ("Step Fu") → rewrite, don't slice;
  inspect real DOM widths after font load.
- Parallel concat of two playlists picked the wrong clips → sequential + duration sums.
- Scene WAV longer than `duration` is a hard error (narration would be cut).
- "直近の試験" can mean several sessions; list them and confirm the target set.
- Watching a video is study support; never mark questions mastered or alter attempts.
