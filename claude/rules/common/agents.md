---
description: Guidance for using Claude subagents only when their extra context and cost are justified.
---

# Agent Orchestration

Agents live in `~/.claude/agents/`. Use them for work that benefits from isolation, specialist review, or parallel investigation. Do not use an agent for simple edits, quick status checks, or work that is clearer in the main session.

## Common Choices

| Agent | Use When |
|-------|----------|
| planner | A feature, refactor, or migration needs a real implementation plan. |
| architect | The task changes system boundaries, data flow, or long-term structure. |
| tdd-guide | A bug or feature needs a test-first loop or careful regression coverage. |
| code-reviewer | A non-trivial code change needs review before landing. |
| language-specific reviewers | A language-specific change has enough risk to justify specialist review. |
| build-error-resolver | A build failure is not obvious after reading the error and local context. |
| security-reviewer | The task touches auth, secrets, permissions, payments, user input, or network boundaries. |
| docs-lookup | Library or API behavior needs current documentation. |

## Parallel Work

Run agents in parallel only when the tasks are independent and the combined result will be better than a single focused pass. Good examples are security plus maintainability review, or separate investigations of unrelated failures.

For complex problems, split perspectives deliberately:
- factual verification
- senior engineering tradeoff review
- security or privacy review
- consistency and redundancy review
