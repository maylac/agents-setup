# Workspace Agent Instructions

## Core Principles (apply to any non-trivial task)

1. **Think before acting** — State your assumptions explicitly. If something is unclear, stop and ask. Surface tradeoffs and alternative interpretations instead of picking one silently.
2. **Simplicity first** — Write the minimum that solves the problem. No speculative features, no abstractions for single-use code, no configurability that wasn't requested.
3. **Surgical changes** — Touch only what the request requires. Match existing style; don't refactor or "improve" adjacent code. Remove only the orphans your own change created — leave pre-existing dead code (mention it instead).
4. **Goal-driven execution** — Turn each task into a verifiable success criterion, then loop until it is met. State a brief plan with per-step checks for multi-step work.

For the full rationale and worked examples, load the `karpathy-guidelines` skill before writing, reviewing, or refactoring code.


## Development Workflow Standard: Backlog.md

When a repository already uses Backlog.md, start with `backlog instructions overview` and follow its local workflow. Use a Backlog task for multi-step work that benefits from durable acceptance criteria; do not initialize it for tiny edits unless the user asks.


## Full-Auto Safety Guardrails

Even in trusted or full-auto sessions, treat external side effects as gated work. Destructive operations, lockfile deletion, force pushes, publishing/uploading/sending/archiving, and payments/trading/account actions require an explicit user request or confirmation. Prefer draft/dry-run/preview first, then report the exact command or action taken and its relevant output.

## Solution Recording (extract-approach)

After solving a hard problem — a bug that required a pivot after a failed approach, an architecture decision with real tradeoffs, or a non-obvious root cause — invoke the `extract-approach` skill BEFORE reporting completion. It records one learnings note (`docs/learnings/` in-repo, `~/tasks/learnings/` otherwise). Skip it for problems solved on the first straightforward attempt. Division of labor: workflow/process lessons still go to `~/tasks/lessons.md`; user/environment facts still go to auto-memory; technical solution records go through this skill.

## Voice Input Assumption

Assume many user prompts are dictated by voice and may contain speech-to-text errors, typos, missing words, or odd punctuation. Infer the intended meaning from context and proceed with the most likely interpretation. Ask a clarifying question only when the ambiguity affects scope, safety, destination, data loss, credentials, or another irreversible choice.

## Tool Use Rules

- Prefer `ax` over `curl` for web fetching and extraction; run `ax agent-context` for detailed syntax. Use curl only for protocol-level work ax cannot perform, and state the exception.
- When asked to verify an X article or linked article, do NOT use Jina Reader (`r.jina.ai`) — deprecated 2026-07 because the API became unreliable. For X posts/articles use `opencli twitter article <URL>`; for other pages use WebFetch (or Exa `web_fetch_exa`). If a login wall or metadata-only result blocks reading, state that limitation explicitly before trying alternatives.
- RTK rewrites common shell commands. If behavior is surprising, use `rtk proxy <cmd>`; prefer `rg` for search and `/usr/bin/find` for compound predicates. See `claude/RTK.md`.

## Local Tools

- `ax`: `$HOME/.local/bin/ax`, source at `~/workspace/tools/ax`.
- `OmniGet`: `~/Applications/omniget.app`, source at `~/workspace/tools/omniget`; use `omniget --source-path` or `omniget --dev` when needed.
- `Maestro`: use the narrowest existing mobile smoke flow first; report a missing simulator/emulator runtime explicitly.

<!-- Maintenance: AGENTS.md is the source of truth (shared tool-agnostically, e.g. with Codex). ~/CLAUDE.md is a symlink to this file — keep the symlink intact. -->
