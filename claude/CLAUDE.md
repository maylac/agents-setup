# Workflow Orchestration

- Planning, verification, and code-quality workflow: see `rules/common/development-workflow.md`, `rules/common/performance.md`, `rules/common/testing.md`, and `rules/common/coding-style.md`.
- Agent and subagent orchestration: see `rules/common/agents.md`.
- TodoWrite and task-tracking mechanics: see `rules/common/hooks.md`.
- Personal workflow thresholds: use plan mode for 3+ step or architectural work; if execution goes sideways, stop and re-plan; summarize changes per step; prove completion with tests, logs, or behavior diff at a staff-engineer bar.
- **Self-improvement loop**: After recurring corrections or durable workflow lessons, record the pattern in `~/tasks/lessons.md` as a rule that prevents recurrence. Review relevant lessons when they are likely to apply.
- **Autonomous bug fixing**: Given a bug report, just fix it -- point at logs/errors/failing tests and resolve, without hand-holding.

# Memory System

Auto-memory lives under `~/.claude/projects/<current-project>/memory/` (types: user, feedback, project, reference). Use it proactively, and **always verify memory against current files before acting** -- paths, names, and state drift.

# Codex Collaboration

For heavy tasks -- long research, multi-file refactors, complex implementation -- consider delegating to `mcp__codex__codex` when it would materially preserve context. Continue sessions with `mcp__codex__codex-reply` + sessionId.

@RTK.md

---

# Coding Behavior

Karpathy Guidelines are maintained in skill `karpathy-guidelines`. Load and follow that skill for coding, review, and refactoring instead of duplicating it here.

For coding, review, or refactoring, apply the Karpathy Guidelines as an execution gate: smallest scoped change, no unrelated cleanup, explicit assumptions when needed, and concrete verification before completion.
