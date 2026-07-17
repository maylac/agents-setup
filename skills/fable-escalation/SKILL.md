---
name: fable-escalation
description: Fable-tier judgment routing - /model fable escalation, desk prep, return rules, and the two sanctioned Fable subagent roles. Triggers on proposing /model fable, escalating to a top-tier model (Fable, or Codex max/ultra effort), desk prep before a high-stakes final judgment, returning from Fable, planning a long exploratory task or hitting 3+ consecutive marginal-gain iterations (advisor checkpoints), or claiming done on expensive-to-reverse work (verifier gate). Not for routine per-subagent model picks.
license: MIT
---

# Fable Escalation

Use this skill when deciding whether to propose `/model fable`, when planning advisor checkpoints or a verifier gate for Fable-tier judgment, when preparing the desk before a Fable review, or when returning from Fable to normal work.

## Routing Tiers

Reserve Fable5 for rare, high-stakes final judgment. Do everyday judgment, review, and writing on Opus4.8; templated execution on Sonnet5; mechanical inspection on Haiku4.5.

| Tier | Alias | Use for |
|------|-------|---------|
| Fable5 | `fable` | Type-less, high-failure-cost, whole-system final judgment. Human-in-the-loop only. |
| Opus4.8 | `opus` | Daily judgment, code review, ambiguous debugging, security, multi-file changes, human-facing writing. |
| Sonnet5 | `sonnet` | Templated mass production and execution: build/type-error fixing, boilerplate, established migrations, E2E generation, loop operation. |
| Haiku4.5 | `haiku` | Mechanical conversion and inspection: format, lint, rename, log/extract, pure doc retrieval. |

Aliases resolve via `~/.claude/settings.json` env such as `ANTHROPIC_DEFAULT_FABLE_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL`.

## Three Ways Into Fable

Match the mode to where the task needs its judgment (task-shape asymmetry):

| Mode | Mechanism | Task shape |
|------|-----------|------------|
| Escalation | `/model fable` main-session switch, human approves | Judgment IS the task: irreversible, whole-system decision |
| Advisor | `fable-advisor` subagent at planned checkpoints | Judgment scattered across the task: exploratory work where each result reshapes what to try next |
| Verifier | `fable-verifier` subagent before "done" | Judgment at the end: expensive-to-reverse completion claim |

Only escalation moves the main session. The two subagent roles are bounded,
read-only consultations that leave the main session on its normal tier — they
exist so unattended or mid-task work can get Fable-tier judgment without
paging the human or paying for a full session switch.

## Strict Fable Policy

- No executor or worker subagent runs on `fable`. Exactly two read-only consultation subagents are sanctioned: `fable-advisor` and `fable-verifier` (sections below). Mass production never runs on Fable.
- Main-session Fable is entered only by switching with `/model fable`, so the human stays in the loop.
- The agent cannot change the main-session model itself. The agent may only propose the switch.
- Propose `/model fable` only when the desk is prepared by lower tiers and the task is one of:
  1. Locking in an irreversible or broadly cascading structural decision, such as a public API, data model, or framework choice.
  2. A type-less, high-failure-cost major decision that needs a whole-system view.
  3. The one-time foundational design of a direction that later drops to mass production.
- After the Fable judgment is fixed, immediately propose returning to `opus`.
- Never propose Fable for everyday writing, review, debugging, maintenance, cheap reversible changes, or locally scoped changes.
- If prep is incomplete, recommend against the switch and finish the desk first. The final call stays with the human — state what is missing rather than blocking.
- After a Fable judgment is fixed, record the reasoning with `extract-approach` before returning to `opus` — that note is what lets lower tiers reuse the judgment.

## Desk Prep Before Fable

Before proposing `/model fable`, lower tiers should finish this checklist:

- Enumerate the full blast radius by machine extraction.
- Visualize dependencies and irreversible points.
- Narrow the decision to 2-3 options with a trade-off table.
- Attach citable primary sources where external facts matter.
- Make lint, tests, and type checks green when relevant.
- Reduce the ask to a single decision.

For the blindspot/option-generation steps, use `know-your-unknowns` patterns 1 (blindspot pass), 3 (design directions), and 5 (intervention spectrum) instead of improvising the same artifacts here.

## Advisor Checkpoints (fable-advisor)

On a long exploratory task, direction re-ranking is NOT the executor's own
call. Executors hill-climb: they keep tuning the current line long after its
expected value has fallen below untried alternatives, and their own "step
back" re-ranking shares the blind spots that got them stuck. Upfront planning
does not fix this — rankings made before data are frequently wrong, sometimes
anti-correlated with what works. Judgment has to be scattered across the
task, not front-loaded.

Use when the task is exploratory (each result reshapes what's worth trying
next) AND long enough that a wrong direction wastes hours of budget:
experiment sweeps, parameter tuning, research loops, iterative optimization.

- Schedule the checkpoints in the plan, at fixed points: after the initial
  plan, then at roughly every 1/3 of the remaining budget. An unscheduled
  checkpoint is a checkpoint that never happens — a rule against omission,
  not a deadline: if a task turns long and exploratory mid-run, insert
  checkpoints from that point onward.
- Also consult off-schedule when 3 consecutive iterations yield marginal
  gains on the same line — that is the hill-climbing signature. This trigger
  applies even when no checkpoints were scheduled.
- Hard cap: at most 3 advisor consults per run, scheduled and off-schedule
  combined, in any session or workflow script. Wanting a 4th is itself a
  signal — surface the situation to the human or settle on the current best
  line.
- Send a compact brief per `fable-advisor`'s input contract: goal + metric,
  results table, candidate directions, remaining budget. No transcripts, no
  whole files.
- Continue the SAME advisor instance via SendMessage at later checkpoints; do
  not spawn a fresh advisor per checkpoint. Accumulated context plus a warm
  prompt cache makes each later consult cheaper and sharper.
- Weight the advisor's mid-task re-rankings over its initial-plan advice; the
  role's value is re-prioritization against observed results.
- The consult does not interrupt the human — this is how an unattended run
  gets Fable-tier judgment without paging anyone.

When NOT to use: short tasks, templated execution, single-pass work. The
handoff cost (see Consultation Cost Discipline) needs enough at stake to pay
for itself.

## Verifier Gate (fable-verifier)

Everyday completion claims keep the normal path: opus code review and
verification-before-completion. The gate applies when the claim precedes an
expensive-to-reverse landing — merges whose post-deploy rollback is costly,
data migrations, security-relevant changes, and outward-facing deliverables
that are hard to retract once shipped (published artifacts, customer-visible
releases, external submissions — not internal drafts or anything a follow-up
message can correct).
"It's still on a branch, so it's reversible" is not an exemption: the gate
exists precisely because pre-merge is the last cheap moment to be wrong, and
"verification maps to the opus tier" does not cover this class — opus review
is desk prep for the gate, not a substitute for it.

- Assemble the brief per `fable-verifier`'s input contract: original ask,
  explicit acceptance criteria, diff scope, and per-criterion evidence.
- The verdict gates the claim. `scoped-incomplete` or `not-done` means the
  next action is closing the named gap (opus-task-loop), not reporting done.
- One verifier call per distinct claim. Re-verification of the same claim is
  allowed only after closing the specific named defects, and both attempts
  count: a second failing verdict goes to the human. Do not tune the artifact
  to satisfy the verifier.
- The gate covers high-stakes claims that do not meet the `/model fable` bar.
  If the work itself qualifies for escalation, do the escalation; the gate is
  not a way around it.

## Consultation Cost Discipline

- Every handoff has a roughly fixed coordination cost: the brief and the
  report are each written once and read once — billed at least twice. Consult
  when the judgment at stake outweighs that; skip when it doesn't.
- Keep briefs compact and self-contained. A results table beats attached
  files; attached files beat a transcript dump.
- Route repeat consults to the same instance so its prompt cache accumulates;
  a fresh spawn re-pays the entire context write.
- For a task that already meets the advisor or verifier bar, a bounded Fable
  consult is usually cheaper than the wandering low-tier exploration it
  replaces. Efficiency never qualifies a task by itself — it only breaks ties
  among tasks that already qualify.

## Fable Window Fallback

Fable access is time-windowed, not permanent (`~/.claude/scripts/fable-window-close.sh`
strips the main-session `model: fable` default once the window closes). When
the window is closed, none of the three modes disappear — they degrade to a
named fallback tier, because the judgment in `fable-advisor.md` and
`fable-verifier.md` is written as a procedure (weight data over priors,
correct hill-climbing, demand independent evidence), not tacit Fable-only
capability:

| Mode | While Fable is open | While Fable is closed |
|------|---------------------|------------------------|
| Escalation | `/model fable`, human approves | Stays on `opus` for final judgment — no fallback switch exists, since there is no session-level model to switch into. Note this limitation explicitly when a task would otherwise have escalated. |
| Advisor | `fable-advisor` (`model: fable`) | Same agent, same brief/output contract, invoked with `model: 'opus'` override (Claude) or `gpt-5.6-sol` high/ultra effort (Codex) |
| Verifier | `fable-verifier` (`model: fable`) | Same agent, same contract, `model: 'opus'` override (Claude) or `gpt-5.6-sol` high/ultra effort (Codex) |

Detecting closure: a `/model fable` proposal that the human declines because
the window is closed, or an explicit "Fable unavailable" from the harness, is
the signal — don't guess from the calendar inside a skill (dates drift; the
closure script is the source of truth). Once closed, drop `fable` from the
Routing Tiers table mentally but keep running the advisor/verifier checkpoints
on their fallback tier; the roles' value is the written judgment process, not
the model brand.

## Codex Side: Max / Ultra (GPT-5.6)

The same "rare, top-tier" discipline applies to Codex escalation knobs
(official guidance: "most tasks don't need Max or Ultra"):

Effort levels for `gpt-5.6-sol` (verified via `codex debug models`, 2026-07-12):
`low` / `medium` / `high` / `xhigh` / `max` / `ultra`.

- `max` effort — "maximum reasoning depth for the hardest problems": a
  **single** hardest problem where quality beats speed (deep root-cause,
  one-shot design lock-in). The Codex analog of a Fable escalation; prepare
  the desk the same way first.
- `ultra` effort — "maximum reasoning with automatic task delegation": max
  depth **plus** parallel sub-work. Reach for it only when the task genuinely
  splits into independent units; for a single-threaded problem, `max` gives
  the same depth for fewer tokens.
- Default remains `gpt-5.6-sol` + `medium` (the model's verified default);
  raise effort stepwise (`high` → `xhigh`) before reaching for `max`.

## Workflow Scripts

Set `agent(..., { model, effort })` per stage:

- Mechanical: `haiku` with low effort.
- Execution: `sonnet`.
- Judgment, verification, synthesis: `opus`.

Never run executor or worker stages on `fable` inside a workflow script. Two
bounded exceptions, when the run meets the bars above: `agentType:
'fable-advisor'` at planned checkpoints (same hard cap of 3 per run) and
`agentType: 'fable-verifier'` once per distinct high-stakes claim (several
gated claims in one run is a smell — surface it). Everything else on Fable
stays human-in-the-loop main-session only.

## Skills

Do not hardcode a model in a skill procedure. Delegate to the tiered subagents above or rely on main-session routing. Third-party skills are left unedited.
