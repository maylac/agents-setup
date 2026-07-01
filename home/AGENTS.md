# Workspace Agent Instructions

## Core Principles (apply to any non-trivial task)

1. **Think before acting** — State your assumptions explicitly. If something is unclear, stop and ask. Surface tradeoffs and alternative interpretations instead of picking one silently.
2. **Simplicity first** — Write the minimum that solves the problem. No speculative features, no abstractions for single-use code, no configurability that wasn't requested.
3. **Surgical changes** — Touch only what the request requires. Match existing style; don't refactor or "improve" adjacent code. Remove only the orphans your own change created — leave pre-existing dead code (mention it instead).
4. **Goal-driven execution** — Turn each task into a verifiable success criterion, then loop until it is met. State a brief plan with per-step checks for multi-step work.

For the full rationale and worked examples, load the `karpathy-guidelines` skill before writing, reviewing, or refactoring code.

## Execution Gate

Before non-trivial code edits:
- Identify the smallest change that satisfies the request.
- State assumptions only when they affect implementation.
- Do not touch unrelated files or refactor adjacent code.
- Verify with the narrowest relevant command before finishing.

## Voice Input Assumption

Assume many user prompts are dictated by voice and may contain speech-to-text errors, typos, missing words, or odd punctuation. Infer the intended meaning from context and proceed with the most likely interpretation. Ask a clarifying question only when the ambiguity affects scope, safety, destination, data loss, credentials, or another irreversible choice.

## Tool Use Rules

- When asked to verify an X article or linked article, check it through Jina Reader first (`https://r.jina.ai/<URL>`, where `<URL>` includes its own scheme). If Jina returns only a login wall or metadata, state that limitation explicitly.
- **RTK**: a PreToolUse hook silently rewrites common Bash commands to token-lean `rtk` equivalents (e.g. `git status` → `rtk git status`). This applies in both Claude Code and Codex sessions. If a command fails unexpectedly, check whether it was rewritten (`rtk proxy <cmd>` runs the raw command for debugging). Known limits: prefer `rg`/`rg --files` for search; use `/usr/bin/find` directly for compound predicates or `-exec` actions, since `rtk find` doesn't support those forms. See `claude/RTK.md` for the full guide (Claude-only file, but the hook and limits apply to both tools).

<!-- Maintenance: AGENTS.md is the source of truth (shared tool-agnostically, e.g. with Codex). ~/CLAUDE.md is a symlink to this file — keep the symlink intact. -->
