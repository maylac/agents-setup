---
name: vantik-weakness-shorts
description: Turn a learner's Vantik wrong-answer history into a batch of Japanese vertical (1080×1920) explainer shorts voiced by VOICEVOX ずんだもん in the approved 鉄則ショート look (dark graphite, official AWS icons), then publish them to the private NAS video library and Vantik's 鉄則ショート list. Source map + batch procedure + known failure modes for 「誤答を潰すショート動画を大量に作って」「弱点解説の縦型動画」「復習動画を増やして」.
---

# Vantik weakness shorts

Done three times for SAP-C02 (38 clips 10/18, 60+60 clips 10/23-24). The renderer,
synthesizer, QA and publish tools already exist; this skill is the map so a new batch
starts from them instead of rewriting. Read `~/tasks/learnings/2026-10-18-video-copy-truncation.md`
and `~/tasks/learnings/2026-10-24-concat-tempfile-collision.md` before producing.

## Design (fixed since 2026-10-26)

Every Vantik short, weakness clips included, uses the approved **鉄則ショート look** from the
`exam-rule-shorts` skill: dark graphite background, large unboxed official AWS Architecture Icons,
4 scenes 場面 → 罠 → 鉄則 → 確認, `series_label` 鉄則. Take the renderer, linter, synthesizer and frame
QA from `~/.claude/skills/exam-rule-shorts/` and follow its content rules (icon on every node, one-line
titles, narration ending 「のだ。」, official Japanese terms). The light box-and-arrow template under
`~/tasks/vantik-sap-video-20261018/` is retired: on 2026-11-14 a DVA batch built with it had to be
redone because it did not match the earlier DVA videos. Before rendering, compare one frame with an
existing clip of the same exam (`~/tasks/rule-shorts-20261026/videos/<prefix>-r01.mp4`).

What stays specific to this skill: evidence from the learner's misses (step 1), grouping misses into
transferable rules, `question_ids`/`attempt_ids` coverage, and the priority-ordered playlists. Local ids
must match the linter (`[a-z]{3}-r\d{2}`, e.g. `dvw-r01`); map them to Vantik ids at publish time.

## Existing pieces (do not re-implement)

| Piece | Where | Notes |
|---|---|---|
| Renderer, linter, frame QA | `~/.claude/skills/exam-rule-shorts/` (`renderer/`, `scripts/lint_content.py`, `scripts/shorts-frames.cjs`) | Icons: link `assets/` from `~/tasks/rule-shorts-20261026/assets`. `node_modules`: link `~/tasks/rule-shorts-20261026/production/node_modules`. |
| VOICEVOX synthesizer (stdlib Python) | `~/.claude/skills/exam-rule-shorts/scripts/synthesize.py` (copied per batch) | Needs the VOICEVOX engine on `127.0.0.1:50021` (if the app is closed, start `/Applications/VOICEVOX.app/Contents/Resources/vv-engine/run --host 127.0.0.1 --port 50021`; localhost needs the sandbox off). Reuses WAVs by text+settings hash; timed file must be named `audio/episodes-timed.json`. |
| Delivery QA (gallery, VTT subtitles, ffprobe + full decode) | `qa_delivery.py` next to the batch | Writes `delivery/qa.json`, `delivery/index.html`. |
| Library packaging / publish script | `~/tasks/dva-shorts-20261113/nas-publish/` (`build.py` merges catalog + manifest, `publish.sh` uploads/swaps/pushes) | Earlier SAP tooling under `~/tasks/sap-c02-final-20261024/nas-publish/` targets the retired review-videos feed. |
| Content schema | `content/episodes.json` of either batch | `id, title, scenes[4]{id,kicker,title,body,caption,narration,nodes[2-4]{label,sub},edges{from,to,label},rule?,wrong?,source_url}`, plus `question_ids, attempt_ids, priority, topic, sources[], quiz{question,answer}, verification_status`. `coverage.json` maps episode → question/attempt IDs. |

## Batch procedure

Work in a new dated folder `~/tasks/<exam>-shorts-<YYYYMMDD>/` with `content/ audio/
production/ videos/ delivery/ evidence/ nas-publish/`. Split ownership the way the
last batch did (content / audio+production / delivery+publish), one owner per folder.

1. **Evidence.** Snapshot the production DB with `vantik-prod-verify` (record SHA-256
   and counts). Latest result per `question_id`, repeated misses first, recent misses
   second. Write `evidence/priority-evidence.json` (top N with IDs) and
   `content/weakness-analysis.md` (domain miss rates = practice history, not a score forecast).
2. **Content.** Use the exam-rule-shorts schema and linter (`python3 tools/lint_content.py` must
   print `content ok`): 場面 = the discriminating condition, 罠 = the learner's actual misconception,
   鉄則 = the correct design and reason, 確認 = one retrieval question with the answer. Group several
   misses into one transferable rule; never recite copyrighted stems or stored answer letters.
   Rewrite to fit; **never slice strings**. Keep `question_ids, attempt_ids, priority, sources, quiz,
   verification_status`; stored keys that look wrong get `needs_review` and a hedged narration.
3. **Audio.** `python3 synthesize.py --input content/episodes.json --all --timed-output audio/episodes-timed.json`.
4. **Render.** As in exam-rule-shorts steps 6-7: `node render.mjs build`, frame QA
   (`shorts-frames.cjs` → `no layout issues`), render in groups, decode-check every MP4, and compare
   one frame side by side with an existing clip of the same exam.
5. **Concat + QA.** Run concatenations **sequentially** (shared `concat-<ms>.txt`
   collides when parallel) and compare each output duration to the sum of inputs.
   `python3 qa_delivery.py --timed-input … --build-gallery --build-subtitles --verify`.
   Look at representative frames at scene transitions.
6. **Publish.** Current path (2026-11): the NAS library (`/volume1/docker/vantik-video-library/current/dist`,
   content-addressed `media/ posters/ captions/` + `catalog.json`) and Vantik's 鉄則ショート list
   (`vantik-content/rule_shorts/manifest.json` → `tools/sync-to-nas.sh`; `GET /api/rule-shorts?exam_code=`).
   The old `review-videos.json` feed is empty and unused. Add a new collection
   (`aws-<exam>-weakness-<YYYYMMDD>`), keep existing catalog/manifest rows byte-identical (indent 1,
   `ensure_ascii=False`, trailing newline), manifest clips get `chapters: []`. In auto mode the
   classifier denies NAS writes even after a chat approval: prepare `nas-publish/publish.sh`
   (upload new files without overwriting, back up + atomically swap `catalog.json`, commit/push the
   manifest, sync) and hand it to the user or Codex to run; then verify read-only (hashes, nginx 200 from
   inside `vantik-video-library`, API counts). Replacing a published batch = new media files + updated
   `src/poster/subtitle` in both JSONs; old files stay for rollback.
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
