---
name: vantik-decisive-highlights
description: Mark, per answer choice, the killer word/phrase that makes a Vantik question's correct choice correct and, separately, the phrase that disqualifies each wrong choice, then apply them to the NAS production DB through additive, reviewed, backed-up waves. Covers every exam and every question (past exams and originals). Use for 「正解の決め手と不正解の理由を別々に強調して」「キラーワードをハイライト」「ハイライトが付いていない選択肢がある」「強調箇所を直して」.
metadata:
  short-description: Correct-reason vs elimination-reason choice highlights
---

# Vantik decisive highlights

Each choice gets source-exact phrases (Japanese and English) stored in `question_key_points` with a `choice_id`. The UI shows them only after grading: correct choices as 「正解の決め手」 (green), wrong choices as 「不正解の決め手」 (red, wavy underline). The role is not stored; the backend derives it from `correct_answers`, so the answer key stays the single source of truth.

Scope is every active question version of every exam, `past_exam` and `original`. The first run (SAP-C02 past exams, 2026-11-07/08, 537 questions / 2,304 choices) is the reference implementation: `scripts/sap_decisive_highlights.py`, `scripts/choice_key_points.py`, `scripts/generate_choice_key_points.py`, `scripts/choice_highlight_render.mjs` in reskilling-os, and `docs/learnings/2026-11-03-choice-highlight-clause-boundaries.md`. Read that note before starting.

## Tooling (any exam)

- Source `decisive-highlights-v1` (reskilling-os commit `1d4ba72`): the backend gives its choice points a `correct_reason` / `elimination_reason` role for every exam and classification. The older `sap-decisive-highlights-v1` source stays limited to SAP past exams.
- `scripts/choice_key_points.py --exam <code> --export` writes the scope (all active versions, past exams and originals). `--manifest m.json` validates exact spans against the served text; `--source decisive-highlights-v1 --apply` replaces the legacy `choice-key-points-tool` rows of each applied choice. A choice with `"hold"` keeps its legacy highlight.
- Before relying on roles in production, confirm `/health` serves a revision that contains `1d4ba72`.
- DVA-C02 reference run (2026-11-08): `~/workspace/maylac/dva-highlights-20261108/` holds `BRIEF.md` (generation rules), `REVIEW.md` (independent review), `build_manifest.py` (merge, exact-span and renderer checks, holds) and `apply_production.sh` (backup, dry run, apply, zero-change rerun, integrity). Copy them for the next exam and change the exam code.
- In the Claude sandbox the venv Python hangs at site startup; run it as `python -S` with `PYTHONPATH=backend:.:<venv site-packages>`.

## What counts as a decisive phrase

- Judge the best answer among the offered choices, not an ideal production design the question did not ask for.
- A correct choice may carry several complementary phrases that together cover each decisive requirement. A wrong choice needs one conclusive flaw.
- The phrase must name what decides this choice against its siblings. A span that is also true of a wrong sibling, or a generic service name, is not decisive.
- The Japanese and English phrases must point at the same requirement or flaw.
- Exact visible text only. Keep identifiers, quantities, negation and paired delimiters whole. Check each phrase through the deployed normalizer and renderer (`choice_highlight_render.mjs`): Q0528 had a phrase spanning an e-mail address that passed text matching but did not render.
- Bind every choice to the stored answer key and the bound explanation rationale. If the answer key, choice text or explanation contradict each other, hold the choice; never invent an elimination reason to fill a gap.

## Workflow

1. **Snapshot (read-only).** Take an SQLite online backup of the live DB and work on the copy. Record `quick_check`, foreign-key violations, and the counts of `attempts` and sessions.
2. **Inventory.** Per exam: question versions, choices, choices that already have rows from this pipeline, and the rows to preserve. Leave manual and prompt-level key points (`choice_id IS NULL`) and other sources untouched.
3. **Generate in parallel.** Split by exam, then in batches of about 50 questions. The generator proposes only semantic decisions and phrases; the host binds opaque stable choice IDs, checks exact spans and hashes, and stores the raw model response with a receipt. Never trust model-supplied IDs, hashes or approval fields.
4. **Independent review per choice.** A different model or harness reviews every candidate against the full question, all siblings and the rationale. Review status lives on the choice. A conflict on a sibling is context, not a reason to hold the other choices: in the first SAP run a whole-question hold rule erased 422 groundable choices and showed up as "some choices have no highlights".
5. **Repair the holds.** Re-propose shorter or more precise phrases for focus, exactness and render failures, then review again. Record each remaining hold with a category (`source_or_answer_key_conflict`, `no_grounded_decisive_distinction`, `missing_required_context`, `unresolved_material_fact`, ...) and its evidence.
6. **Build a manifest per wave and prove it on a copy.** Apply to a disposable DB copy, then rerun: the rerun must change 0 rows. Every previously approved row must stay identical, including row ID and metadata. `quick_check=ok`, foreign-key violations 0, and no change to questions, answers, explanations, other sources or learning history.
7. **Apply to production.** Run the guarded applier with the manifest SHA-256, the code hashes and the expected `/health` revision pinned. It must take its own online backup first, keep the write lock short (no full-DB hashing inside `BEGIN IMMEDIATE`), write only `question_key_points`, and log JSONL. Ship good choices in waves rather than waiting for the last hold.
8. **Verify live.** Check the API for every question in scope: roles, phrases and choice IDs match the manifest, and history rows that existed before the wave are unchanged (new answers from normal use are expected). Then make a GET-only browser check at 390×844 on two or three affected questions, in Japanese and English, light and dark: nothing is visible before grading, and both roles are visible after it.

## Production access

- Production DB: `/app/data/vantik.db` in container `vantik` on the NAS, reached through `ssh ugnas`. If its mDNS name does not resolve, use the Tailscale override from the local SSH config and auto-memory; never write addresses into this skill.
- `scp` to the NAS fails; pipe scripts and manifests over stdin with `docker exec -i`.
- Offline packs downloaded earlier keep their old highlights until they are downloaded again. Mention this in the report.

## Report

Japanese, short: per exam, the choices highlighted before → after, rows added, held choices by category with example question IDs, the backup paths, copy and live verification results, and the UI check. Do not report a wave as live without the production apply log and the live verification file.
