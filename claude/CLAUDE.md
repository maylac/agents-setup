# Workflow

- Home-wide principles and safety rules are single-sourced in `~/AGENTS.md`; scoped rules under `rules/` load when matching files are touched.
- Use plan mode for ambiguous, architectural, or 3+ step work. For bug reports, inspect evidence, fix the root cause, and verify without unnecessary hand-holding.
- Route recurring workflow lessons through the `self-improve` skill. Technical solutions that required a real pivot go through `extract-approach`.
- Use built-in Explore/Plan for read-only discovery. Use custom subagents only when isolation, specialist review, or parallel work materially helps.

# Design Quality

Before user-facing UI work, load `~/.claude/DESIGN.md` and follow its pre-ship process.

# Memory System

Use auto-memory proactively, but verify paths, names, and state against current files before acting.

# Model Routing

The default is `opusplan`: Opus for planning and Sonnet for execution. Use `fable-escalation` before proposing Fable; reserve Fable for high-cost-to-reverse final judgment.

# Codex Collaboration

For heavy research or implementation, delegate to Codex when it materially preserves Claude context; continue with the returned session ID.
