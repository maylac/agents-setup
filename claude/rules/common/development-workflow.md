---
description: Conditional workflow guidance for non-trivial implementation work.
---

# Development Workflow

Use this workflow for non-trivial implementation, refactoring, or debugging. For small edits, prefer the smallest local change plus a targeted verification.

## Research And Reuse

Start with the current repository: existing patterns, helper APIs, tests, and docs. Use current library documentation for version-sensitive API behavior. Search package registries, GitHub, or broader web sources when you are considering a new dependency, a template, or an unfamiliar implementation strategy.

Do not do external research just because a small local pattern is already clear.

## Plan First

For work with three or more meaningful steps, architectural impact, or ambiguous requirements, state assumptions and a short plan before editing. Planning docs such as PRDs, architecture notes, or task lists are only needed when the task asks for them or the work is large enough to benefit from a durable artifact. This is about drafting/documenting a plan, not the tool's plan mode — see `rules/common/performance.md` (Plan Mode) for when to actually enter plan mode.

## Testing Approach

Use tests proportional to risk. For bug fixes, prefer a regression test that fails before the fix when practical. For new behavior, add or update the narrowest test that proves the requested behavior. Use the repository's own coverage targets when they exist; do not impose a global coverage percentage.

## Review

Review non-trivial diffs for regressions, scope creep, missing verification, and security-sensitive changes before calling the work complete. Use a reviewer agent only when the extra pass is likely to catch issues the main session might miss.

A review counts as done only when each of these has an explicit written answer:
- blast radius: what breaks first if this diff is wrong, and who notices
- riskiest line: which single change is most likely to be wrong, and which check actually exercised it
- out of scope: what was deliberately not done, stated so the next session doesn't rediscover it

## Commit And Push

Follow the repository's git workflow and the user's explicit request. Do not create commits or pushes just because this workflow was loaded.
