---
name: fable-escalation
description: /model fable escalation decisions, desk prep checks, and return rules. Triggers on proposing /model fable, escalating to a top-tier model (Fable, or Codex max/ultra effort), desk prep before a high-stakes final judgment, or returning from Fable. Not for routine per-subagent model picks.
license: MIT
---

# Fable Escalation

Use this skill when deciding whether to propose `/model fable`, when preparing the desk before a Fable review, or when returning from Fable to normal work.

## Routing Tiers

Reserve Fable5 for rare, high-stakes final judgment. Do everyday judgment, review, and writing on Opus4.8; templated execution on Sonnet5; mechanical inspection on Haiku4.5.

| Tier | Alias | Use for |
|------|-------|---------|
| Fable5 | `fable` | Type-less, high-failure-cost, whole-system final judgment. Human-in-the-loop only. |
| Opus4.8 | `opus` | Daily judgment, code review, ambiguous debugging, security, multi-file changes, human-facing writing. |
| Sonnet5 | `sonnet` | Templated mass production and execution: build/type-error fixing, boilerplate, established migrations, E2E generation, loop operation. |
| Haiku4.5 | `haiku` | Mechanical conversion and inspection: format, lint, rename, log/extract, pure doc retrieval. |

Aliases resolve via `~/.claude/settings.json` env such as `ANTHROPIC_DEFAULT_FABLE_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL`.

## Strict Fable Policy

- No subagent is pinned to `fable`.
- Fable is entered only by switching the main session with `/model fable`, so the human stays in the loop.
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

Legacy note: `~/.codex/fugu-mini.config.toml` / `fugu-ultra.config.toml` and
the `[model_providers.fugu]` block are GPT-5.5-era leftovers, superseded by
the native `ultra` effort level. Do not route escalations through them.

## Workflow Scripts

Set `agent(..., { model, effort })` per stage:

- Mechanical: `haiku` with low effort.
- Execution: `sonnet`.
- Judgment, verification, synthesis: `opus`.

Never use `fable` inside a workflow script. Fable is human-in-the-loop main-session only.

## Skills

Do not hardcode a model in a skill procedure. Delegate to the tiered subagents above or rely on main-session routing. Third-party skills are left unedited.
