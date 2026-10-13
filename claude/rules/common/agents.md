---
paths:
  - "**/.claude/agents/**"
  - "**/.codex/agents/**"
  - "**/AGENTS.md"
description: Guidance for using Claude subagents only when their extra context and cost are justified.
---

# Agent Orchestration

Agents live in `~/.claude/agents/`. Use them for work that benefits from isolation, specialist review, or parallel investigation. Do not use an agent for simple edits, quick status checks, or work that is clearer in the main session.

## Common Choices

Follow the Claude model and effort defaults in `~/.claude/CLAUDE.md`; a task-level model choice takes priority. Use the table below to select a bounded agent when needed.

| Agent | Use When |
|-------|----------|
| main session | Architecture or multi-step work benefits from a concise plan. |
| implementation-worker | An approved bounded edit or test run benefits from parallel execution; assign owned files and acceptance criteria. |
| code-reviewer | A material risky change needs one independent review before landing. |
| build-error-resolver | A real build failure is not obvious after reading the error and local context. |
| security-reviewer | A material change to auth, secrets, permissions, payments, user input, or network boundaries needs one focused review. |
| fable-advisor | A long exploratory task hits a planned checkpoint or 3+ consecutive marginal-gain iterations and needs its remaining directions re-ranked (bar and hard cap in `fable-escalation`). |
| fable-verifier | A completion claim precedes an expensive-to-reverse landing and needs a final verification gate (bar in `fable-escalation`). |

## Parallel Work

Run agents in parallel only when the tasks are independent and the combined result will be better than a single focused pass. Good examples are security plus maintainability review, or separate investigations of unrelated failures.

Split only independent work that benefits from parallel execution; avoid repeated review passes over the same change.
