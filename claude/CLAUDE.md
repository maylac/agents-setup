# Workflow Orchestration

- Planning, verification, and code-quality workflow: see `rules/common/development-workflow.md`, `rules/common/performance.md`, `rules/common/testing.md`, and `rules/common/coding-style.md`.
- Agent and subagent orchestration: see `rules/common/agents.md`.
- When a language-specific rule (`rules/<language>/`) conflicts with `rules/common/`, the language-specific rule takes precedence.
- TodoWrite and task-tracking mechanics: see `rules/common/hooks.md`.
- Personal workflow thresholds: plan mode trigger — see `rules/common/performance.md` (Plan Mode); summarize changes per step; prove completion with tests, logs, or behavior diff at a staff-engineer bar.
- **Self-improvement loop**: After recurring corrections or durable workflow lessons, record the pattern in `~/tasks/lessons.md` as a rule that prevents recurrence. Review relevant lessons when they are likely to apply. Workflow/process lessons go in `~/tasks/lessons.md`; facts about the user or environment go in auto-memory.
- **Autonomous bug fixing**: Given a bug report, just fix it -- point at logs/errors/failing tests and resolve, without hand-holding.

# Memory System

Auto-memory lives under `~/.claude/projects/<current-project>/memory/` (types: user, feedback, project, reference). Use it proactively, and **always verify memory against current files before acting** -- paths, names, and state drift.

# Prompt Interpretation

See the Voice Input Assumption in `home/AGENTS.md` (loaded as `~/AGENTS.md` / `~/CLAUDE.md`) — same rule, single source.

# Codex Collaboration

For heavy tasks -- long research, multi-file refactors, complex implementation -- consider delegating to `mcp__codex__codex` when it would materially preserve context. Continue sessions with `mcp__codex__codex-reply` + sessionId.

@RTK.md

---

# Coding Behavior

See the Core Principles and Execution Gate in `home/AGENTS.md` (loaded as `~/AGENTS.md` / `~/CLAUDE.md`) — same rule, single source. Karpathy Guidelines are maintained in skill `karpathy-guidelines`; load and follow that skill for coding, review, and refactoring instead of duplicating it here.
