---
description: Guidance for using Claude subagents only when their extra context and cost are justified.
---

# Agent Orchestration

Agents live in `~/.claude/agents/`. Use them for work that benefits from isolation, specialist review, or parallel investigation. Do not use an agent for simple edits, quick status checks, or work that is clearer in the main session.

## Common Choices

| Agent | Use When |
|-------|----------|
| planner | A feature, refactor, migration, or system-boundary decision needs a real implementation plan. |
| code-reviewer | A non-trivial code change needs review before landing. |
| build-error-resolver | A build failure is not obvious after reading the error and local context. |
| security-reviewer | The task touches auth, secrets, permissions, payments, user input, or network boundaries. |

## Parallel Work

Run agents in parallel only when the tasks are independent and the combined result will be better than a single focused pass. Good examples are security plus maintainability review, or separate investigations of unrelated failures.

For complex problems, split perspectives deliberately:
- factual verification
- senior engineering tradeoff review
- security or privacy review
- consistency and redundancy review
