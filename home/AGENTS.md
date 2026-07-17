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

Recall side: before starting deep debugging, a design decision, or a non-obvious investigation, search the target repo's `docs/learnings/` (or `~/tasks/learnings/`) for an existing note on the theme and read it first.

## Voice Input Assumption

Assume many user prompts are dictated by voice and may contain speech-to-text errors, typos, missing words, or odd punctuation. Infer the intended meaning from context and proceed with the most likely interpretation. Ask a clarifying question only when the ambiguity affects scope, safety, destination, data loss, credentials, or another irreversible choice.

## Tool Use Rules

- Prefer `ax` over `curl` for web fetching and extraction; run `ax agent-context` for detailed syntax. Use curl only for protocol-level work ax cannot perform, and state the exception.
- When asked to verify an X article or linked article, do NOT use Jina Reader (`r.jina.ai`) — deprecated 2026-07 because the API became unreliable. For X posts/articles use `opencli twitter article <URL>`; for other pages use WebFetch (or Exa `web_fetch_exa`). If a login wall or metadata-only result blocks reading, state that limitation explicitly before trying alternatives.
- RTK rewrites common shell commands. If behavior is surprising, use `rtk proxy <cmd>`; prefer `rg` for search and `/usr/bin/find` for compound predicates. See `claude/RTK.md`.

## Cross-Harness Model Routing (Hermes, Codex, and Antigravity)

- Treat `gpt-5.6-sol` as the coordinator, architect, and bounded advisor—not the default executor for every subtask in either Hermes or Codex.
- Aggressively offload eligible lightweight work to Antigravity/Gemini by default instead of waiting for an explicit delegation request. Route lookup, file/location discovery, inventory, summarization, extraction, classification, formatting, documentation drafts, test-case enumeration, deterministic review checklists, and other bounded mechanical work to `Gemini 3.5 Flash (Low)`; use `Gemini 3.5 Flash (Medium/High)` for scoped implementation, test generation, and routine fixes; and `Gemini 3.1 Pro (High)` only when a stronger non-Codex worker is justified. Keep work in SOL/Codex only when it is too small to amortize launch overhead, requires Codex-specific state/tools, or needs coordinator judgment.
- For one-shot read-only or self-contained tasks, invoke `agy --print "<task contract>" --model "<model>" --print-timeout 5m`. In Hermes, prefer the enabled `antigravity_delegate` tool, which performs the same explicit model-pinned dispatch and records a routing audit receipt. For longer interactive work, use the `agmsg` Antigravity driver (`~/.agents/skills/agmsg/scripts/spawn.sh antigravity <name> --project <repo> --team hermes --model "<model>" --boot-prompt "<task contract>"`) so completion evidence can return through the shared team.
- In Hermes, keep the main session on SOL for decomposition, acceptance criteria, synthesis, and final judgment. Route eligible work to Antigravity first; use Hermes delegation pinned in `~/.hermes/config.yaml` to `gpt-5.6-terra` when Antigravity is unsuitable or unavailable. Do not perform delegated implementation in the SOL parent. Before reporting completion, cite at least one successful non-SOL routing receipt for every non-trivial task, or state the concrete exception that kept execution in SOL.
- In Codex, route eligible work to Antigravity before spawning Codex workers. Use installed `gpt-5.6-terra` agents for work requiring Codex-specific tools or context, and `gpt-5.6-luna` agents for lightweight fallback work.
- Do not spawn SOL workers by inheritance when an Antigravity, Terra, or Luna worker can perform the task. SOL may execute only trivial, bounded work where delegation overhead would exceed the work itself, or when workers are unavailable; state that exception briefly.
- Fan out only independent subtasks, give every worker explicit acceptance criteria and output boundaries, and independently verify material outputs before synthesis. The daily harness report flags SOL above 50% of token usage as routing drift.

## Local Tools

- `ax`: `$HOME/.local/bin/ax`, source at `~/workspace/tools/ax`.
- `OmniGet`: `~/Applications/omniget.app`, source at `~/workspace/tools/omniget`; use `omniget --source-path` or `omniget --dev` when needed.
- `Maestro`: use the narrowest existing mobile smoke flow first; report a missing simulator/emulator runtime explicitly.

<!-- Maintenance: AGENTS.md is the source of truth (shared tool-agnostically, e.g. with Codex). ~/CLAUDE.md is a symlink to this file — keep the symlink intact. -->

## Plan Infographic Approval Gate

Plan mode の plan が ExitPlanMode で承認されたら、実装着手前に必ず `plan-infographic`
スキルを実行する（plan保存 → NotebookLMでインフォグラフィック生成 → PNG/モバイル通知/URL配信 →
AskUserQuestionで承認確認）。インフォグラフィックの承認が返るまで実装コードを編集しない。
パイプラインが失敗した場合はエラーを報告し、テキスト plan のまま AskUserQuestion 承認に
降格して進める。
