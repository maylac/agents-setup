---
name: fable-escalation
description: "Route work within the configured Claude Fable harness: protect its Fable budget, prepare high-stakes decisions, and apply its independent verifier or advisor roles. Do not use for Codex/Astra routing or routine worker selection."
license: MIT
---

# Fable Escalation

Use this Claude-only compatibility skill only when the user explicitly requests the legacy Fable workflow and the active Claude harness exposes the aliases and roles described below. It does not configure models or apply to Codex/Astra or another runtime. If the requested Fable route is unavailable, report that and stop; do not switch models silently.

Before applying a routing rule, confirm the active harness actually exposes the relevant alias, agent, and configuration. If it does not, retain the decision discipline inline and do not invent a Fable fallback.

## Standing-Fable routing

For the local Claude setup whose main session is `fable` and whose weekly Fable budget is capped, reserve Fable for judgment, planning, review, and user-facing synthesis. Route implementation, long tool loops, mechanical inspection, and repetitive verification to the configured lower-cost executor tiers.

- Do not run ordinary executor or worker tasks on Fable.
- Keep a compact, evidence-backed brief for any expensive judgment: the decision, 2–3 viable options, blast radius, tests or checks already run, and primary sources when external facts matter.
- Check for an explicit rate-limit notice or observed model change before relying on a Fable-specific role. Do not infer exhaustion from the calendar.
- When the cap is exhausted, report that the requested route is unavailable. Use another model only if the user explicitly names it.

## Independent verifier gate

Use the configured `fable-verifier` only before an expensive-to-reverse landing: a costly rollback, data migration, security-sensitive change, public release, or external submission. Ordinary scoped work follows normal verification.

Give the verifier the original request, acceptance criteria, diff or artifact scope, and evidence per criterion. A `scoped-incomplete` or `not-done` verdict means close the named gap before claiming completion. Re-run once only after addressing the identified defect; if the same claim fails again, report the evidence to the user.

For machine-checkable properties such as schema conformance, counts, cross-references, or link validity, run the relevant deterministic check. A plausible output or a clean command exit is not enough evidence.

## Exploratory advisor

Use `fable-advisor` only when the Fable main session is unavailable and a long exploratory task needs its remaining directions re-ranked after evidence arrives. It is not useful for short, templated, or single-pass work.

At most three consultations per run. Give the same advisor a compact goal, metric, results table, candidate directions, and remaining budget; continue the same instance for later checkpoints. Escalate the situation to the user when a fourth consultation would be needed.

## Boundaries

This skill preserves the Claude-specific policy and its learned verifier invariant. It does not require a Fable review for routine completion, does not override user authorization, and does not impose Fable aliases or roles on other harnesses.
