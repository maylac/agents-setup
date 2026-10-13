# Workspace Agent Instructions

## Core Principles (apply to any non-trivial task)

1. **Think before acting** — State material assumptions and success criteria. Ask when ambiguity changes scope, safety, destination, credentials, data loss, or another consequential choice. For ordinary ambiguity, make a reasonable assumption, say what it is, and proceed.
2. **Simplicity first** — Write the minimum that solves the problem. No speculative features, no abstractions for single-use code, no configurability that wasn't requested.
3. **Surgical changes** — Touch only what the request requires. Match existing style; don't refactor or "improve" adjacent code. Remove only the orphans your own change created — leave pre-existing dead code (mention it instead).
4. **Goal-driven execution** — Turn each task into a verifiable success criterion, then loop until it is met. State a brief plan with per-step checks for multi-step work.

For the full rationale and worked examples, load the `karpathy-guidelines` skill before writing, reviewing, or refactoring code.

In autonomous runs (below), "ask" means only the Hard Stops list; for everything else, decide, record the assumption in the report, and proceed.

## Autonomous Operation: Slack → Dots → Mac mini

The user operates from Slack and does not touch a PC. The home Mac mini is the always-on mothership where all local execution happens.

- **Roles.** ChatGPT Dots is the orchestrator: it takes the user's request in Slack, decomposes it, writes task contracts, dispatches them, judges returned evidence, and reports back. Agents run on the Mac mini: Claude Code owns implementation, debugging, refactoring, and review of material changes; Antigravity (`agy`) owns bounded mechanical work — lookup, inventory, extraction, summarization, doc drafts, test enumeration. Dots does not implement; agents do not re-scope.
- **Task contract.** One dispatch = one Slack thread (or linked GitHub issue) stating: goal, repo/path, owned files, acceptance criteria as runnable checks, agent and model, time budget. The agent replies in the same thread with: status (done / blocked / failed), changed files, each check command with pass/fail, commit or PR link, and at most 5 lines of notes. No transcripts or full diffs.
- **Dispatch.** Dots reaches the Mac mini through ChatGPT's built-in Mac connection; no separate bridge is needed. From there, run agents non-interactively inside a dedicated git worktree for the task: `claude -p "<contract>"` with permissions pre-approved in settings, or `agy --print "<contract>" --model "<model>" --print-timeout 30m`. Prefer these CLI routes over GUI or browser automation. If the Mac connection or an agent login is down, report that in Slack rather than asking the user to operate the Mac.
- **Token efficiency.** Use the cheapest capable agent: Antigravity Flash for mechanical work, Claude for code. Contracts carry paths and criteria, not pasted file contents. Agents read focused files, run the narrowest relevant checks, and stop when they pass. After two failed approaches, stop and report blocked with evidence. Dots spot-checks only material or risky changes instead of re-running everything. Dots-dispatched agents do not start extra cross-harness splits unless the contract allows it.
- **No human PC operation.** Never ask the user to click, unlock, log in, or run a command on the Mac. Use CLI, SSH, launchd, and APIs. If something truly needs a human (OS permission dialog, hardware, 2FA), post it in Slack as a blocker with the exact single action required, and continue other unblocked work.


## Development Workflow Standard: Backlog.md

When a repository already uses Backlog.md, start with `backlog instructions overview` and follow its local workflow. Use a Backlog task for multi-step work that benefits from durable acceptance criteria; do not initialize it for tiny edits unless the user asks.


## Autonomy and Hard Stops

The user pre-authorizes autonomous execution through implementation. Do not ask for confirmation to plan, read, create or edit files, install project dependencies, run builds and tests, create branches or worktrees, commit, push non-default branches, or open PRs. Finish with the PR ready and a Slack report; merging to the default branch happens on the user's reply unless the repo explicitly enables auto-merge.

Hard stops — prepare a draft or dry run, post one approval request in the Slack thread, and keep doing other unblocked work:

- Force pushes or history rewrites on shared branches; lockfile deletion.
- Irreversible deletion outside the task worktree (databases, backups, cloud resources).
- Payments, trading, purchases, and account, credential, or permission changes.
- Publishing, uploading, or sending to anyone other than the user (public posts, emails, releases, store or KDP submissions); production deploys.
- Restarting shared daemons that kill running agents (for example Paseo).

Silence or timeout is never approval. Report the exact command or action taken and its relevant output.

## Solution Recording (extract-approach)

After solving a hard problem — a bug that required a pivot after a failed approach, an architecture decision with real tradeoffs, or a non-obvious root cause — invoke the `extract-approach` skill BEFORE reporting completion. It records one learnings note (`docs/learnings/` in-repo, `~/tasks/learnings/` otherwise). Skip it for problems solved on the first straightforward attempt. Division of labor: workflow/process lessons still go to `~/tasks/lessons.md`; user/environment facts still go to auto-memory; technical solution records go through this skill.

Recall side: before starting deep debugging, a design decision, or a non-obvious investigation, search the target repo's `docs/learnings/` (or `~/tasks/learnings/`) for an existing note on the theme and read it first.

## Voice Input Assumption

Assume many user prompts are dictated by voice and may contain speech-to-text errors, typos, missing words, or odd punctuation. Infer the intended meaning from context and proceed with the most likely interpretation. Ask a clarifying question only when the ambiguity affects scope, safety, destination, data loss, credentials, or another irreversible choice.

## Tool Use Rules

- Use a web-fetching or browser tool available in the current session. Prefer `ax` for web fetching when `command -v ax` succeeds; check `ax agent-context` for current syntax. Use `curl` only for protocol-level work or when the preferred tool is unavailable, and state why.
- Do not use Jina Reader (`r.jina.ai`) for article verification. For X articles, use `opencli twitter article <URL>` only when `opencli` is installed and its current help supports that command. If a login wall blocks access, state the limitation; do not treat a title, snippet, or metadata-only result as verified article content.
- RTK may rewrite tool commands only when the CLI is installed and the relevant `PreToolUse` hook is registered. Check both before relying on it; see `~/.claude/RTK.md` for measured historical caveats. For exact file-parity checks, use `cmp` or checksums rather than trusting rewritten `diff` output.
- Start code discovery with `rg` or Read. Use `graphify explain "<symbol>"` only when Graphify is available and the target repo has `graphify-out/graph.json`; treat graph results as incomplete evidence and check source files. Past checks found queries can miss relevant nodes and path names can be ambiguous. Follow the Graphify skill and current local help for build or refresh steps.

## Cross-Harness Model Routing

- **Claude Code routing:** Native Claude role guidance lives in `~/.claude/CLAUDE.md` and live settings; use the user's configured Claude model unless they choose otherwise. Claude-owned execution uses that configured model (currently Opus 5.5 at medium effort); Codex-owned execution follows the Astra/Luna routing below. Those Astra/Luna bullets apply to Codex sessions and Codex-owned subwork; Claude main-session planning and judgment keep native Claude routing. Explicit task-level model choices win.
- Use `gpt-6-astra` for planning, architecture, supervision, review judgments, synthesis, and final decisions. Use `gpt-6-luna` for implementation, fixes, research, extraction, documentation, test execution, and mechanical evidence collection.
- Keep role boundaries explicit: Luna gathers and reports review evidence; Astra assesses that evidence and decides whether the work meets its criteria. For non-trivial tasks, Astra plans and supervises while Luna performs the work. Astra may handle a genuinely trivial operation directly when delegation overhead exceeds the work.
- Respect a user's explicit model choice for the task or subtask. If the requested model or routing path is unavailable, stop that route and report the availability issue; do not silently fall back to another model.
- Codex sessions use native delegation. In Hermes, delegate through an available Codex route; do not configure OpenAI models as native Hermes models.
- Before reporting non-trivial implementation complete, identify the execution owner and provide evidence they performed the work. Codex-owned execution uses Luna unless the task is genuinely trivial or that route is unavailable; Claude-owned execution uses Claude's configured model. A read-only peer judgment does not require spawning an execution worker. Astra remains accountable for Codex supervision and final assessment.
- Fan out only independent subtasks, give each worker explicit acceptance criteria and output boundaries, and have Astra independently assess material results before synthesis.

## Cross-Harness Collaboration

- By default, split actionable work across Claude and Codex when a useful bounded division exists: assign one independent subtask to the opposite harness while the owner advances a distinct part. Do not wait for a failure or special review trigger. Favor useful work across both available harness budgets over minimizing invocation count; avoid overlap and chat loops. Keep truly trivial or indivisible tasks local; do not use “routine” or “reversible” alone as a reason to skip a useful split. Honor explicit model choices and opt-outs.
- The main session owns scope, integration, and the final decision. Default to one external worker; add another only for independent work that benefits from parallel execution. In work mode, assign owned paths and acceptance criteria so workers do not overlap. The owner may issue bounded revisions or follow-on tasks as needed; do not duplicate work or create chat loops.
- Distinguish work from consultation: work mode may edit only its assigned files and run task-relevant local checks; consultation mode is read-only, with one consultation and at most one focused follow-up before reassessing. Read-only consultation peers marked `CROSS_HARNESS_PEER=1` or `delegated peer` must not start another cross-harness call, native delegation, or child task.
- Delegated work agents, including those marked `CROSS_HARNESS_WORKER=1`, may re-delegate bounded, independent subtasks through cross-harness calls, native delegation, or child tasks within their assigned scope without seeking fresh approval for delegation itself. Pass on applicable instructions, file ownership, acceptance criteria, model choices, and execution limits; avoid overlapping work and recursive delegation loops, verify child results, and report them to the parent. Re-delegation does not expand permissions or authorize external side effects; existing approval requirements and runtime policies still apply.
- Use the `cross-harness-collab` skill to dispatch the opposite-harness slice or request a read-only judgment as appropriate. If that route is unavailable, state that and continue authorized work in the current harness without claiming the other harness participated. This policy covers bounded local edits and tests within the user's task, not unrelated external side effects.

## Local Tools

- For NAS work, use the existing SSH alias `ugnas` first. It was verified on 2026-09-27; Vantik commands run through `ssh ugnas` and `docker exec vantik`. Check current SSH connectivity before falling back to a browser or asking the user to unlock the home Mac. The user needs NAS work to continue while away from home; do not assume physical access to the Mac. Read or write the live SQLite DB inside the container, and use SQLite online backups for local inspection instead of opening the live DB over SMB.
- Check that a tool is installed and supported before relying on it. For OmniGet, use `omniget --source-path` or `omniget --dev` only when the installed CLI's current help supports those options. For mobile checks, use the narrowest existing Maestro smoke flow and report a missing CLI or simulator runtime.

<!-- Maintenance: AGENTS.md is the source of truth (shared tool-agnostically, e.g. with Codex). ~/CLAUDE.md is a symlink to this file — keep the symlink intact. -->

## Plan Infographic Approval Gate

This gate applies only to interactive sessions where the user personally entered Plan mode. Skip it for Dots/Slack-dispatched runs; the task contract is the approved plan.

When a Plan-mode plan has been approved by the user, run the `plan-infographic` skill before implementation and wait for the user's approval of its result before editing implementation code. Use named controls such as `ExitPlanMode` or `AskUserQuestion` only when the active harness exposes them; otherwise use its supported approval input or ask for an explicit reply. If the infographic pipeline or a required integration is unavailable or fails, report that and request approval of the text plan. Never treat a timeout or silence as approval.
