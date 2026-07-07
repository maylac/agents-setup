---
name: compact-prep
description: Prepare a durable handoff before running /compact in Claude Code. Use directly as /compact-prep when context is high or before manual compaction.
disable-model-invocation: true
---

# Compact Prep

Prepare a compact-safe handoff that survives Claude Code's natural-language compaction.

## Current Workspace Snapshot

```!
pwd
git branch --show-current 2>/dev/null || true
git status --short 2>/dev/null || true
git diff --stat 2>/dev/null || true
```

## Instructions

Write one concise `Compact Handoff` block in the conversation. Do not edit project files unless the user explicitly asks.

Include these fields:

- Objective: the user's current goal in one sentence.
- Current state: what has already been done and what is verified.
- Decisions: important choices and why they were made.
- Rejected paths: approaches that were considered and should not be repeated.
- Files and commands: files read or edited, and verification commands already run.
- Open issues: unresolved questions, blockers, or risks.
- Next actions: the exact next 1-3 steps after compaction.

Keep it factual and specific. Prefer concrete paths, command names, counts, and error text over general summaries. If a field is unknown, write `none observed` rather than inventing details.

End with: `Next: run /compact, then continue from this handoff.`

## When to compact

Use this table to decide when compaction is worth it (compact at a phase boundary, not mid-task):

| Phase Transition | Compact? | Why |
|-----------------|----------|-----|
| Research → Planning | Yes | Research context is bulky; plan is the distilled output |
| Planning → Implementation | Yes | Plan is in TodoWrite or a file; free up context for code |
| Implementation → Testing | Maybe | Keep if tests reference recent code; compact if switching focus |
| Debugging → Next feature | Yes | Debug traces pollute context for unrelated work |
| Mid-implementation | No | Losing variable names, file paths, and partial state is costly |
| After a failed approach | Yes | Clear the dead-end reasoning before trying a new approach |
