# Workspace Agent Instructions

## Core Principles (apply to any non-trivial task)

1. **Think before acting** — State your assumptions explicitly. If something is unclear, stop and ask. Surface tradeoffs and alternative interpretations instead of picking one silently.
2. **Simplicity first** — Write the minimum that solves the problem. No speculative features, no abstractions for single-use code, no configurability that wasn't requested.
3. **Surgical changes** — Touch only what the request requires. Match existing style; don't refactor or "improve" adjacent code. Remove only the orphans your own change created — leave pre-existing dead code (mention it instead).
4. **Goal-driven execution** — Turn each task into a verifiable success criterion, then loop until it is met. State a brief plan with per-step checks for multi-step work.

For the full rationale and worked examples, load the `karpathy-guidelines` skill before writing, reviewing, or refactoring code.


## Development Workflow Standard: Backlog.md

Use Backlog.md as the default task ledger for non-trivial development work in Git repositories. When a repo already has Backlog.md initialized, start by running `backlog instructions overview` and follow its local workflow. For multi-step features, bug fixes, or refactors, prefer a Backlog task with a clear description, acceptance criteria, and implementation notes before changing code. Keep work scoped to one task at a time and update the task status/notes as the implementation is verified.

Common commands:
- `backlog init "Project Name"` — initialize a repo-local Markdown task board when the project does not already have one and the user wants durable task tracking.
- `backlog instructions overview` — read project-specific Backlog/agent instructions after initialization.
- `backlog board` — inspect current task state.
- `backlog task create ...` / `backlog task edit ...` — create or update task specs and acceptance criteria.

Do not add Backlog.md files to tiny one-off edits unless the user asks for durable project tracking or the repo already uses Backlog.md.

## Execution Gate

Before non-trivial code edits:
- Identify the smallest change that satisfies the request.
- State assumptions only when they affect implementation.
- Do not touch unrelated files or refactor adjacent code.
- Verify with the narrowest relevant command before finishing.

## Solution Recording (extract-approach)

After solving a hard problem — a bug that required a pivot after a failed approach, an architecture decision with real tradeoffs, or a non-obvious root cause — invoke the `extract-approach` skill BEFORE reporting completion. It records one learnings note (`docs/learnings/` in-repo, `~/tasks/learnings/` otherwise). Skip it for problems solved on the first straightforward attempt. Division of labor: workflow/process lessons still go to `~/tasks/lessons.md`; user/environment facts still go to auto-memory; technical solution records go through this skill.

## Voice Input Assumption

Assume many user prompts are dictated by voice and may contain speech-to-text errors, typos, missing words, or odd punctuation. Infer the intended meaning from context and proceed with the most likely interpretation. Ask a clarifying question only when the ambiguity affects scope, safety, destination, data loss, credentials, or another irreversible choice.

## Tool Use Rules

- When asked to verify an X article or linked article, check it through Jina Reader first (`https://r.jina.ai/<URL>`, where `<URL>` includes its own scheme). If Jina returns only a login wall or metadata, state that limitation explicitly.
- **RTK**: a PreToolUse hook silently rewrites common Bash commands to token-lean `rtk` equivalents (e.g. `git status` → `rtk git status`). This applies in both Claude Code and Codex sessions. If a command fails unexpectedly, check whether it was rewritten (`rtk proxy <cmd>` runs the raw command for debugging). Known limits: prefer `rg`/`rg --files` for search; use `/usr/bin/find` directly for compound predicates or `-exec` actions, since `rtk find` doesn't support those forms. See `claude/RTK.md` for the full guide (Claude-only file, but the hook and limits apply to both tools).

## Local Tools

- **OmniGet**: installed at `/Users/maylac/Applications/omniget.app`; source checkout at `/Users/maylac/workspace/tools/omniget`. Use `omniget` to launch, `omniget --version` to verify, `omniget --source-path` to locate the repo, and `omniget --dev` from any directory to start the Tauri dev app.

<!-- Maintenance: AGENTS.md is the source of truth (shared tool-agnostically, e.g. with Codex). ~/CLAUDE.md is a symlink to this file — keep the symlink intact. -->
