---
name: vantik-question-pruning
description: Shrink a Vantik exam's question pool for fast study by deactivating stale, unreliable-answer, and duplicate questions on the NAS production DB (backup → dry-run → apply, reversible). Use for requests like 「過去問を絞って」「古い問題・解説不十分を除外」「重複を減らして」「この問題数を回す時間はない」.
metadata:
  short-description: Prune stale/unreliable/duplicate Vantik questions
---

# Vantik question pruning

Turns a large imported pool (typically ExamTopics past exams) into a short study set without losing history. Questions are never deleted: `questions.active=0` plus a dated note in `questions.note`, so the admin UI (`PATCH` active/note) can restore any of them. The importer does not reactivate them.

## Connect

- Production DB: `/app/data/vantik.db` inside container `vantik` on the NAS.
- `ssh ugnas` first. If its mDNS host does not resolve (away from home), override `HostName` with the NAS's Tailscale address and set `HostKeyAlias` to the original host name; take both from the local SSH config and auto-memory (never write them into this public skill).
- `scp` to the NAS fails; pipe files over stdin: `ssh … 'docker exec -i vantik sh -c "cat > /tmp/prune.py && /app/.venv/bin/python /tmp/prune.py ARGS"' < scripts/prune.py`.

## Workflow

1. **Survey (read-only).** Count active questions per source and classification; check whether the source text has `コミュニティ投票:` lines (the vote rules need them) and whether every question has an `ai_generated` explanation.
2. **Stale terms (research every time; do not reuse an old list blindly).** Web-search current retirements, renames, and end-of-support notices for the exam's subject area (for AWS: retired services, renamed services, support-plan changes). Write a JSON `{"regex": "reason"}` file and pipe it into the container too. Match it against the prompt plus correct answers. Then read the matched questions: drop only those where the retired item is the **answer or premise**. A retired item that appears only as a distractor is harmless. Pass the reviewed list with `--stale-terms`, or hand-pick the IDs.
3. **Dry-run** `prune.py --exam <code> [--unreliable] [--stale-terms f.json] [--dedupe] [--max-low-vote N] --list`. Check the counts, the drop reasons, the domain mix before and after (it must stay close to the official weights), and that `missed_kept` equals the number of missed questions.
4. **Backup, then apply.** `cd /app && .venv/bin/python -m reskilling_os backup`, then rerun the same args with `--apply`.
5. **Verify.** Pipe `scripts/vantik_integrity_check.py` from the reskilling-os repo into the container with argument `/app/data/vantik.db`. Every `check` must be 0 except `inactive_question_in_active_source`, which counts these deactivations.

## Rules (the levers, in order of safety)

- `--unreliable`: no choice-level AI explanation; top community vote ≠ displayed answer; or top vote share < 0.6 (`--min-share`).
- `--dedupe`: one question per identical correct-answer text. Recognition exams (CLF, AIF-style "use case → service") lose almost no coverage this way: CLF went from 609 to 373. The kept representative is a previously missed question if there is one, else the one with the most votes (the canonical wording, usually with the richest discussion).
- `--max-low-vote N`: also drop never-missed questions with ≤ N total votes. Use this only when the user wants still fewer questions; report the resulting count first.
- Questions the user has answered wrong are never dropped by dedupe or low-vote rules.
- Answer-text dedupe is weaker for scenario-heavy exams (SAP/DOP-style, where the same service answers different problems). There, prefer `--unreliable` and stale terms, and show sample groups before deduping.

## Report

Japanese, short: before → after count, counts per reason with example IDs, the domain mix, the backup path, the integrity result, and how to restore (admin UI, or `update questions set active=1` on the IDs whose note carries the tag). Production writes outside question `active`/`note` are not covered by this skill.
