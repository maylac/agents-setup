---
name: quota-burndown
description: Spend a subscription's remaining usage window (Codex/ChatGPT weekly quota, Claude rate window) on bounded, verifiable, non-duplicating work before a reset, with explicit stop conditions and an executor/auditor split. Use when the user says 「リセット来るからトークン使い切って」「残りの枠を有効活用して」「Codexと相談して枠を使って」; not for ordinary tasks that happen to be large.
---

# Quota burndown

Ran twice (2026-10-13, 2026-10-18). The user wants **results, not consumption**: no
filler, no duplicate research, no invented problems, stop at the reset. Treat it as a
mini-programme with a control file, a progress log and an index of finished artifacts.

## Set up (first 5 minutes)

1. Create `~/tasks/codex-usage-<YYYYMMDD>/` (or `claude-usage-…`) with
   `CONTROL.md`, `PROGRESS.md`, `INDEX.md`. Read the previous run's `INDEX.md` and
   `CONTROL.md` first; completed or deliberately stopped items are not reopened.
2. Measure the window: in Codex call `get_usage_limits` (record used %, remaining %,
   `resetsAt`); in Claude Code use `/usage` output as reported by the user or the
   session's rate-limit events. Write the baseline into `CONTROL.md`.
3. Write the **scope**: default to the user's current focus (recently: Vantik /
   current exam) and read-only investigation + local artifacts. Unless the user says
   otherwise, no repo commits, no production DB writes, no deployments, no payments,
   no shared-daemon restarts, no publishing.
4. Write the **stop conditions**: quota reached; reset observed (usage drops or
   `resetsAt` changes); the scheduled reset time; usage cannot be measured; candidate
   list exhausted; user says stop. Quota that appears *after* the reset is not spent.

## Pick work

- Ask the other harness (Codex thread or Claude via `cross-harness-collab`
  consultation) for up to 6 non-overlapping candidates; the parent decides and records
  the order in `CONTROL.md`. Good candidates: verify stored answer keys against official
  docs, coverage inventories, audit of existing materials, spec reports per gap,
  read-only code investigations with a written status. Bad: re-verifying finished items,
  generic summaries, "exploring".
- Each candidate gets an owned file path, a 15-minute budget and an acceptance check.
  Freeze the denominator (e.g. "133 sections") and never confuse a partial ledger with
  the whole.

## Run loop (batches of 3)

1. Executor (Codex: `gpt-6-luna`; Claude: implementation-worker) produces the artifact
   in its owned file.
2. Independent auditor (Codex: `gpt-6-astra` or sol; Claude: code-reviewer) checks it;
   the executor never self-approves. Unresolved findings go back once.
3. Parent integrates, appends to `INDEX.md` (finished items only) and to `PROGRESS.md`
   with: timestamp, usage % + `resetsAt`, who did what, checks, next three items.
4. Re-measure usage after every batch. Compare with the previous value; a drop or a
   new `resetsAt` means reset → stop and report.
5. If an automation/heartbeat is used to continue between turns, set it to the batch
   cadence, point it at this folder, and **PAUSE it in the file and in the tool** when
   the candidates are done.

## Rules

- Opening an official page is not verification; the claim must be in the page and
  quoted with URL and access date.
- Separate "the stored answer", "the official spec", and "the unique correct answer"
  in every report; past learning data carries its snapshot date.
- When the user later says "finish what is unfinished", resume only listed open items;
  do not search for new candidates.
- Final report (Japanese): usage at start/end and whether a reset was observed, count of
  audited artifacts with links to `INDEX.md`, what was explicitly not done, and that
  no repo/production/billing state changed.
