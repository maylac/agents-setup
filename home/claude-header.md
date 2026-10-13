# Workflow

- Home-wide principles and safety rules are single-sourced in `~/AGENTS.md` and loaded through the `~/CLAUDE.md` symlink. Claude Code's project `AGENTS.md` loading depends on the active version and memory mode; check the loaded instructions and explicitly read the applicable project `AGENTS.md` if it is absent. If cwd is outside `$HOME` (for example, a temp worktree), read `~/AGENTS.md` before side-effectful work.
- When the active session supports plan mode, use it for ambiguous requirements, architectural work, or decisions that need user review before edits. For ordinary multi-step work, state a brief plan and proceed. For bug reports, inspect evidence, fix the root cause, and verify without unnecessary hand-holding.
- Route recurring workflow lessons through the `self-improve` skill. Technical solutions that required a real pivot go through `extract-approach`.
- Follow shared model-routing and cross-harness collaboration policy in `~/AGENTS.md`. In Claude Code, see the Claude agent and performance rules for native routing and bounded delegation. For Codex, follow Astra/Luna routing.

# Design Quality

Before user-facing UI work, load `~/.claude/DESIGN.md` when it exists. Otherwise resolve `~/.claude/CLAUDE.md` and read the sibling `DESIGN.md`. Follow its pre-ship process and use a task-relevant design skill available in the current session.

# Memory System

Use auto-memory proactively, but verify paths, names, and state against current files before acting.

# Model Routing

Use Claude's configured model for Claude-owned execution; the current main-session default is Opus 5.5 at medium effort unless the user chooses otherwise. Use one high-effort Opus review for a material risky change; reserve xhigh for exceptional tasks. Fable agents are opt-in. For ordinary actionable work with a useful division, dispatch one bounded task to the opposite harness while advancing a separate part locally, following the shared policy below.

## Token Efficiency

Prefer deterministic tools and focused reads over broad context gathering. Request concise worker evidence. Stop when relevant checks pass, and rerun broader checks only after a change, failure, or specific unresolved risk. Use a short plan for complex work; reassess after two identical failed approaches.

# Cross-Harness Collaboration

Follow the default cross-harness collaboration policy in `~/AGENTS.md` and use the `cross-harness-collab` skill for the opposite-harness task or read-only consultation. Keep ownership and acceptance criteria explicit; peer-marked tasks cannot delegate again.

# Mobile Completion Reporting

Use mobile completion notifications only when the hook is registered and its target script exists. Do not claim a notification was delivered without success evidence. Preserve any installed hook wiring; when it is absent, report completion in the current task.
