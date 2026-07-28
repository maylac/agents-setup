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
- RTK rewrites common shell commands — a PreToolUse hook that swaps the command string (`rg`/`grep` → `rtk grep`, `find` → `rtk find`, `cat` → `rtk read`). If behavior is surprising, use `rtk proxy <cmd>`; prefer `rg` for search and `/usr/bin/find` for compound predicates. Two traps: `rtk grep` discards `-c`, so a count-only query returns the full digest instead (measured: 4 B raw → 3.4 KB) — use `rtk proxy rg -c` when you want just a number. And the rewrite only fires on simple command shapes, so anything inside `$(...)` or a shell loop runs the real binary unrewritten — never measure or compare RTK from inside command substitution, and don't conclude a search tool is broken from results gathered that way. See `claude/RTK.md`.
- Every git repo under `$HOME` has an AST-only `graphify-out/graph.json` (built 2026-07-28; code files only — docs and markdown are absent, ~32% of all files indexed). Use `graphify explain "<symbol>"` once you have a symbol name: it returns the defining `file:line` plus typed `imports`/`calls`/`contains` edges, which raw search cannot. Do NOT use `graphify query "<natural language>"` as a `rg` replacement — measured on two repos (one at 82% coverage) it anchored on the wrong start nodes and missed answers `rg` returned in ~0.02 s; even an exact-symbol query truncates on hub symbols (664 nodes found, 64 shown — raise with `--budget`). `graphify path "A" "B"` resolves ambiguously and reports "no path" when two files share a basename. So: `rg`/Read stay the default for "where is X"; reach for `graphify explain` for relationships around a known symbol. Refresh with `graphify update .` (AST-only, no API cost) when the graph is stale (source newer than `graph.json`, or `graphify-out/needs_update` exists).

## Cross-Harness Model Routing (Hermes, Codex, and Antigravity)

- Treat `gpt-5.6-sol` as the coordinator, architect, and bounded advisor—not the default executor for every subtask in either Hermes or Codex.
- Implementation, test generation, and routine fixes default to Codex `gpt-5.6-terra` (primary executor — 2026-07-26 decision). Offload bounded mechanical work — lookup, file/location discovery, inventory, summarization, extraction, classification, formatting, documentation drafts, test-case enumeration, deterministic review checklists — to Antigravity `Gemini 3.5 Flash (Low)` by default; use `Gemini 3.1 Pro (High)` only when a stronger non-Codex worker is justified for non-implementation work. Keep work in SOL only when it is too small to amortize launch overhead or needs coordinator judgment.
- For one-shot read-only or self-contained tasks, invoke `agy --print "<task contract>" --model "<model>" --print-timeout 5m`. In Hermes, prefer the enabled `antigravity_delegate` tool, which performs the same explicit model-pinned dispatch and records a routing audit receipt. For longer interactive work, use the `agmsg` Antigravity driver (`~/.agents/skills/agmsg/scripts/spawn.sh antigravity <name> --project <repo> --team hermes --model "<model>" --boot-prompt "<task contract>"`) so completion evidence can return through the shared team.
- In Hermes, keep the main session on SOL for decomposition, acceptance criteria, synthesis, and final judgment. Route implementation to `gpt-5.6-terra` via Hermes delegation (pinned in `~/.hermes/config.yaml`) by default, and bounded mechanical work to Antigravity. Do not perform delegated implementation in the SOL parent. Before reporting completion, cite at least one successful non-SOL routing receipt for every non-trivial task, or state the concrete exception that kept execution in SOL.
- In Codex, `gpt-5.6-terra` agents are the default executors for implementation; route bounded mechanical work to Antigravity, and use `gpt-5.6-luna` agents for lightweight fallback work.
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
