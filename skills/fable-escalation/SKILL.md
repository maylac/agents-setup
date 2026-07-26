---
name: fable-escalation
description: Fable-standing model routing - budget discipline for the Fable 5 main session (permanent on Max at 50% of weekly limits), what stays off Fable, the fable-verifier gate, and fallback routing when the cap is exhausted. Triggers on deciding where implementation or high-volume tool loops should run, desk prep before a high-stakes final judgment, claiming done on expensive-to-reverse work (verifier gate), suspected cap exhaustion or silent fallback to a lower tier, long exploratory tasks while off Fable (advisor checkpoints), or escalating Codex to max/ultra effort. Not for routine per-subagent model picks.
license: MIT
---

# Fable Routing (Standing-Fable Regime)

Since 2026-07-20 Fable 5 is permanent on the Max plan at 50% of weekly usage
limits, and it is the main-session default (`~/.claude/settings.json` →
`"model": "fable"`). The discipline inverted from the escalation era: the
question is no longer "when may we go up to Fable" but "what must stay OFF
Fable" so the weekly cap covers a full week of judgment.

## Routing Tiers

| Tier | Alias | Use for |
|------|-------|---------|
| Fable5 | `fable` | Main session only: judgment, planning, review, user-facing reporting. |
| Opus5 | `opus` | Execution orchestration: workflow scripts, parallel-subagent fleets, review/verification subagents. Session fallback tier (`opusplan`) when the Fable cap is exhausted. |
| Sonnet5 | `sonnet` | Claude-side templated execution when external delegation overhead isn't justified. |
| Haiku4.5 | `haiku` | Mechanical conversion and inspection: format, lint, rename, log/extract, pure doc retrieval. |

Implementation defaults to Codex `gpt-5.6-terra`; Antigravity Gemini takes
bounded mechanical work only (Cross-Harness Model Routing in `~/AGENTS.md`).
Opus5 sits within ~0.5% of Fable5 on agentic-coding benchmarks at half the
per-token cost, so the fallback tier loses little.

Aliases resolve via `~/.claude/settings.json` env such as
`ANTHROPIC_DEFAULT_FABLE_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`,
`ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL`.

## Budget Discipline (protect the 50% cap)

- The main session spends Fable tokens on judgment, planning, review, and
  reporting. Implementation, long tool loops, mass file edits, and repetitive
  verification runs do not belong on the main session — delegate to Codex
  `gpt-5.6-terra` (implementation), `opus` workflows/subagents (execution
  orchestration), or `haiku`/Gemini (mechanical).
- No executor or worker subagent runs on `fable`. In the standing regime
  exactly one Fable subagent stays sanctioned: `fable-verifier`.
  (`fable-advisor` is an off-Fable fallback tool — see below.)
- Workflow scripts never run stages on `fable`; the lone exception is
  `agentType: 'fable-verifier'`, once per distinct high-stakes claim (several
  gated claims in one run is a smell — surface it).
- Watch for silent fallback: at the cap the session may drop to a lower tier
  without ceremony, so you may be running as Opus while believing you are
  Fable. Treat that possibility as standing — it is why the main loop's own
  "verified" claim never substitutes for the verifier gate (worked case
  below).
- When the cap is exhausted mid-week: drop the session to `opusplan` and
  continue. In that state the old escalation rules apply — propose `/model
  fable` only for an irreversible, whole-system final judgment, prepare the
  desk first, and return to `opus` immediately after the judgment is fixed.
- After any Fable-tier judgment on a hard problem, record the reasoning with
  `extract-approach` — that note is what lets lower tiers reuse the judgment.

## Desk Prep Before High-Stakes Judgment

Before locking in an irreversible or broadly cascading decision (public API,
data model, framework choice) on the main session, have lower tiers finish
this checklist first — Fable time is for the judgment, not the paperwork:

- Enumerate the full blast radius by machine extraction.
- Visualize dependencies and irreversible points.
- Narrow the decision to 2-3 options with a trade-off table.
- Attach citable primary sources where external facts matter.
- Make lint, tests, and type checks green when relevant.
- Reduce the ask to a single decision.

For the blindspot/option-generation steps, use `know-your-unknowns` patterns 1
(blindspot pass), 3 (design directions), and 5 (intervention spectrum) instead
of improvising the same artifacts here.

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

With Fable as the standing main-session model, the gate's value is
**independent context**, not tier superiority: a fresh `model: fable` subagent
judges the evidence without the main loop's accumulated blind spots, and it
still judges at true Fable tier even when the main session has silently fallen
back to a lower model.

- Assemble the brief per `fable-verifier`'s input contract: original ask,
  explicit acceptance criteria, diff scope, and per-criterion evidence.
- The verdict gates the claim. `scoped-incomplete` or `not-done` means the
  next action is closing the named gap (opus-task-loop), not reporting done.
- One verifier call per distinct claim. Re-verification of the same claim is
  allowed only after closing the specific named defects, and both attempts
  count: a second failing verdict goes to the human. Do not tune the artifact
  to satisfy the verifier.
- When the deliverable has machine-checkable properties — character-limit
  counts, cross-reference integrity (underline/blank ↔ question ↔ answer),
  link liveness, schema conformance — require script verification, never eye
  or self-report. Worked case (2026-07-18): the main loop, running as Opus but
  believing it was Fable, asserted "integrity self-verified" on five exam
  questions that in fact carried 13 character-limit overruns and blanks absent
  from the body; every defect surfaced only at the fable-verifier gate, and
  the fixes were then delegated to Codex. Treat a confident self-review on
  exact-count/exact-correspondence work as unverified until a script or the
  gate confirms it.

## Advisor Checkpoints (fable-advisor) — off-Fable only

While the main session runs on Fable, do not consult `fable-advisor`: it is a
same-tier consultation that pays the handoff cost for no judgment upgrade —
the Fable main loop re-ranks its own directions. The role applies when the
main session is running below Fable (cap exhausted, `opusplan` fallback, or a
non-Fable harness) on a long exploratory task.

In that state, direction re-ranking is NOT the executor's own call. Executors
hill-climb: they keep tuning the current line long after its expected value
has fallen below untried alternatives, and their own "step back" re-ranking
shares the blind spots that got them stuck. Upfront planning does not fix
this — rankings made before data are frequently wrong, sometimes
anti-correlated with what works.

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

When NOT to use: the main session is already on Fable, short tasks, templated
execution, single-pass work. The handoff cost (see Consultation Cost
Discipline) needs enough at stake to pay for itself.

## Consultation Cost Discipline

- Every handoff has a roughly fixed coordination cost: the brief and the
  report are each written once and read once — billed at least twice. Consult
  when the judgment at stake outweighs that; skip when it doesn't.
- Keep briefs compact and self-contained. A results table beats attached
  files; attached files beat a transcript dump.
- Route repeat consults to the same instance so its prompt cache accumulates;
  a fresh spawn re-pays the entire context write.
- Efficiency never qualifies a task by itself — it only breaks ties among
  tasks that already qualify.

## Cap-Exhausted Fallback

When the weekly Fable cap is spent (or Fable errors out), the roles degrade to
named fallback tiers — the judgment in `fable-advisor.md` and
`fable-verifier.md` is written as a procedure (weight data over priors,
correct hill-climbing, demand independent evidence), not tacit Fable-only
capability:

| Mode | While Fable is available | While the cap is exhausted |
|------|--------------------------|-----------------------------|
| Main session | `model: fable` default | Drop to `opusplan`; note the downgrade to the human. `/model fable` proposals resume next weekly reset. |
| Advisor | Not used (same tier as main) | `fable-advisor` with `model: 'opus'` override (Claude) or `gpt-5.6-sol` high/ultra effort (Codex) |
| Verifier | `fable-verifier` (`model: fable`) | Same agent, same contract, `model: 'opus'` override (Claude) or `gpt-5.6-sol` high/ultra effort (Codex) |

Detecting exhaustion: an explicit rate-limit notice, or a silent model
downgrade you notice mid-session, is the signal — don't guess from the
calendar. Keep running the verifier gate on its fallback tier; the roles'
value is the written judgment process, not the model brand.

## Codex Side: Max / Ultra (GPT-5.6)

`gpt-5.6-terra` is the default implementation executor (see Routing Tiers).
The same "rare, top-tier" discipline as Fable escalation applies to the SOL
effort knobs (official guidance: "most tasks don't need Max or Ultra"):

Effort levels for `gpt-5.6-sol` (verified via `codex debug models`, 2026-07-12):
`low` / `medium` / `high` / `xhigh` / `max` / `ultra`.

- `max` effort — "maximum reasoning depth for the hardest problems": a
  **single** hardest problem where quality beats speed (deep root-cause,
  one-shot design lock-in). The Codex analog of a Fable-tier judgment; prepare
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
- Execution: `sonnet` (or delegate the stage to Codex `gpt-5.6-terra` outside
  the workflow when it is real implementation).
- Judgment, verification, synthesis: `opus`.

Never run executor or worker stages on `fable` inside a workflow script. One
bounded exception, when the run meets the bar above: `agentType:
'fable-verifier'` once per distinct high-stakes claim (several gated claims in
one run is a smell — surface it). `agentType: 'fable-advisor'` stages apply
only to off-Fable runs (Cap-Exhausted Fallback), same hard cap of 3.

## Skills

Do not hardcode a model in a skill procedure. Delegate to the tiered subagents above or rely on main-session routing. Third-party skills are left unedited.
