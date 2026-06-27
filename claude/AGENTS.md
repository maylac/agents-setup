# Claude Config Agent Instructions

This directory contains user-level Claude Code configuration. Keep instruction files short and factual; put reusable procedures in skills or scoped rules instead of duplicating long guidance here.

## Local Map

- `CLAUDE.md` is the Claude Code entry point for this config tree.
- `rules/common/` contains shared user rules. Prefer path-scoped frontmatter for rules that only apply to code or test files.
- `skills/` is a symlink mirror of the canonical shared skill store at `~/.agents/skills`.
- `agents/` contains Claude subagent definitions. Use them only when their extra context and cost are justified.

## Working Agreements

- `~/AGENTS.md` is the tool-agnostic home instruction source, and `~/CLAUDE.md` points to it.
- Karpathy Guidelines live in the shared `karpathy-guidelines` skill; load that skill for coding, review, or refactoring instead of copying its full text here.
- Before changing symlinks, skills, or rules, check the live filesystem state and preserve existing mirrors.
