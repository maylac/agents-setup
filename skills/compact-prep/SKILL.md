---
name: compact-prep
description: Prepare a durable conversation handoff before manual /compact in Claude Code. Invoke directly when compaction is imminent; it does not apply to Codex/Astra unless their active interface requests an equivalent handoff.
disable-model-invocation: true
---

# Compact Prep

Before manual Claude Code compaction, write one concise `Compact Handoff` block in the conversation. Do not edit project files unless the user asked for an edit.

Take a current workspace snapshot when a repository is involved:

```bash
pwd
git branch --show-current 2>/dev/null || true
git status --short 2>/dev/null || true
git diff --stat 2>/dev/null || true
```

Include:

- Objective
- Verified current state
- Decisions and rejected paths
- Files, commands, and observed results
- Open issues, blockers, or risks
- The next 1–3 concrete actions

Use exact paths, commands, counts, and errors. Say `none observed` for an unknown field instead of filling it from memory. End with `Next: run /compact, then continue from this handoff.`

Compact at a phase boundary when the resulting handoff can replace bulky context: after research, after resolving a failed approach, or before switching to unrelated work. Do not compact mid-implementation when the active details are still needed.
