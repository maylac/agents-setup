# Workflow

- Home-wide principles and safety rules are single-sourced in `~/AGENTS.md`; they auto-load for any session whose cwd is under `$HOME` (parent traversal, verified 2026-07-17), and scoped rules under `rules/` load when matching files are touched. If cwd is outside `$HOME` (temp worktree, scratchpad), read `~/AGENTS.md` before side-effectful work.
- Use plan mode for ambiguous, architectural, or 3+ step work. For bug reports, inspect evidence, fix the root cause, and verify without unnecessary hand-holding.
- Route recurring workflow lessons through the `self-improve` skill. Technical solutions that required a real pivot go through `extract-approach`.
- Use built-in Explore/Plan for read-only discovery. Use custom subagents only when isolation, specialist review, or parallel work materially helps.

# Design Quality

Before user-facing UI work, load `~/.claude/DESIGN.md` and follow its pre-ship process.

# Memory System

Use auto-memory proactively, but verify paths, names, and state against current files before acting.

# Model Routing

The default is `opusplan`: Opus for planning and Sonnet for execution. Use `fable-escalation` before proposing Fable; reserve Fable for high-cost-to-reverse final judgment. Two sanctioned Fable subagents cover mid-task judgment without a session switch: `fable-advisor` checkpoints during long exploratory tasks, and the `fable-verifier` gate before expensive-to-reverse completion claims (bars and cadence in `fable-escalation`).

# Codex Collaboration

For heavy research or implementation, delegate to Codex when it materially preserves Claude context; continue with the returned session ID.

# Mobile Completion Reporting

Completion, error, and approval-wait events reach the user's phone through `~/.agents/hooks/notify-mobile.sh` (Telegram via ccgram's bot when configured, Slack DM fallback via `hermes send`). Do not remove its hook wiring; when a long unattended task ends, the Stop hook is the delivery path — no extra action needed.
