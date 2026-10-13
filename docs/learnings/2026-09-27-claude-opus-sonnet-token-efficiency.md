# Balance Claude main-session reasoning with bounded Sonnet execution

- Date: 2026-09-27
- Area: agents-setup / Claude Code model routing
- Type: design-tradeoff

## Problem

The previous shared routing instructions sent Claude planning, implementation, and review to Codex. The user first requested a Claude harness using Opus 5.5, then clarified that best-practice, token-efficient routing was welcome. Live settings, the portable settings snapshot, agent frontmatter, and Desktop Remote Control controls also have distinct owners and scopes.

## Rejected approaches

- Route all work through Codex Astra/Luna from Claude: adds cross-harness handoffs and conflicts with the user's request for a capable native Claude setup.
- Interpret the Opus 5.5 request as a requirement to pin every Claude agent to Opus: spends high-tier reasoning on bounded execution that does not need it.
- Force Sonnet for every exploration step or switch models mid-session: adds routing overhead and fragments the main context.
- Replace live settings wholesale from the portable template: would activate unrelated plugins and hooks instead of changing only the requested model and Remote Control behavior.

## Effective approach

Keep Opus 5.5 at medium effort in the main session for understanding, planning, integration, and difficult implementation. Keep small cohesive tasks local; use one optional Sonnet 5 medium worker for approved, bounded edits or tests when parallel execution saves time or context. Use one high-effort Opus review for material risky changes. Respect task-level model choices, avoid silent fallback, and keep Fable compatibility roles opt-in. Store effort under per-model `modelSettings`, preserve the comprehensive snapshot for backup, and update live settings narrowly.

## Why it works

It preserves strong reasoning at task boundaries and avoids spending it on mechanical work, while leaving delegation conditional on actual parallel benefit. User settings use per-model `modelSettings` for Opus 5.5 because their legacy top-level `effortLevel` is ignored for that model; in project, managed, or `--settings` sources, the same top-level key applies to all models. The backup projection therefore preserves it when present. Runtime evidence: a no-override CLI smoke returned Opus 5.5 as the canonical model; a separate no-tools worker smoke showed an Opus parent forwarding to Sonnet 5 without a model override, with `HARNESS_WORKER_OK` from the child and `HARNESS_ROUTE_OK` from the parent. The CLI reported `/rc active`; after the user completed trusted-device sign-in, the browser displayed Connected via Remote Control and the local session history. That verified a session at that time, not an always-running Remote Control server. Desktop prompt suggestions and Classify session states are off. The initial `/context` observation (106 skills / 8.6k tokens; 5 agents / 376 tokens) predates the final agent mirror sync, so total savings are not yet measured.

## General principles

- Use a high-reasoning main model and a bounded lower-cost worker only when the task split saves more than it costs in context and coordination.
- Keep live configuration narrow; a recovery snapshot may contain unrelated settings and should not be applied as a whole without review.

## 2026-09-27 addendum: On-demand cross-harness peer input (initial choice, superseded)

The initial design, recorded here as history, made automatic Claude↔Codex collaboration an on-demand read-only consultation, not a per-task handoff or persistent hook loop. It triggered for consequential ambiguous design choices, two repeated failures, or one material-risk review; keep the main session as owner and final judge. Cap the route at one consultation plus one focused follow-up, and mark peer briefs so they cannot recursively delegate. A callable CLI helper provides a bounded, auditable invocation without adding another background service. If the route is unavailable, continue the authorized native work and state that no independent review occurred. Existing sessions may retain already-loaded policy; new sessions reliably load updates.

Historical runtime evidence for the consult route: the helper unit suite passed 8/8 tests, `quick_validate.py` separately validated skill frontmatter, and real peer calls succeeded in both directions. Claude's initial Opus 5.5 high-effort review and focused medium-effort follow-up verified canonical model metadata; the follow-up stayed within Read/Glob/Grep and confirmed the revised helper's read-only, non-delegating role. The review found and prompted fixes for interrupted-child cleanup, ambiguous multi-model receipts, and irrelevant plan/delegation bootstrap text. Codex's Astra low smoke found the expected sign bug, but the installed CLI did not expose observed-model metadata, so its model identity remains unverified. Codex input changed from 23,715 to 23,477 tokens in a comparison run that also enabled experimental `skip_host_skill_discovery`, alongside `project_doc_max_bytes=0` and hook disabling; cache state differed, and the roughly 1% change does not demonstrate material savings. The experimental flag was removed. Tiny consultations were skipped and briefs kept narrow.

The Codex helper uses its installed auth while bypassing user config and execpolicy rules; it keeps the read-only sandbox and ephemeral session. `project_doc_max_bytes=0` and hook disabling apply only to this invocation, so provide any necessary repo rules explicitly. Claude initially rejected `--mcp-config '{}'` with `mcpServers: Invalid input` before making a model call; using the valid `{"mcpServers":{}}` structure fixed it. A simulated non-Codex PATH lacked the Desktop-bundled Codex binary, so `~/.local/bin/codex` now points to the verified bundled executable; no global config or auth was changed.

## 2026-09-27 update: Default work split across harnesses (current)

The user stated a preference to use available Claude capacity and divide normal tasks between Claude and Codex. The advice-only rule optimized for fewer peer calls; the current priority is using both harnesses when a useful independent split can make progress. Normal actionable tasks now assign at least one bounded subtask to the other harness through `consult.py --mode work`, while the owner advances an independent part. Tiny or indivisible tasks and simple answers stay local.

Tradeoff: more invocations and coordination overhead in exchange for parallel progress across both available harnesses. Controls keep this bounded: the main session owns planning, integration, and final decisions; one external worker by default; explicit disjoint `--owned-path` ownership and acceptance checks; no recursive delegation or duplicated work. Owned paths are an instruction-level contract, not a per-file sandbox, so the owner inspects and verifies changes, including after a timeout or error. Work defaults are Codex `gpt-6-luna` high and Claude `claude-opus-5-5` medium; consult mode stays read-only (Astra low / Opus medium) with one pass plus one focused follow-up, which does not cap further distinct work tasks. Work receipts use `status: "returned"` and `task_verified: false`; they record a response, not verified task success. Preflight errors set `partial_changes_possible: false`; failures after launch set it true.

Runtime evidence: the helper unit suite passed 14 focused tests, including symlink/bundled-host path resolution; `quick_validate.py` separately validates skill frontmatter. Claude's work call returned with canonical `claude-opus-5-5` verified; medium effort was requested. The owner reviewed changes in the three assigned files. The first Codex work attempt incorrectly reported success even though the response said `codex-code-mode-host` could not start. A second attempt still failed after adding only the bundle directory to child `PATH`, and reported a returned, unverified response with no file change. Resolving the Codex symlink to the actual executable for `argv[0]`, as well as prepending its bundle directory to child `PATH`, fixed the runner lookup. The final Codex call wrote exact `WORK_MODE_OK\n` to the assigned file; owner checks confirmed the sentinel was unchanged and no extra files appeared. Its receipt remained `returned`/unverified by design. It requested Luna high, but the CLI emitted no observed-model metadata, so the serving model remains unverified. Usage was 46,833 input tokens (29,184 cached), 149 output tokens and 35 reasoning tokens, over 9.052 seconds.

## 2026-09-27 addendum: Remote Control needs a running host

`remoteControlAtStartup=true` and Desktop's **Connect new sessions to Remote Control** preference affect session startup; they do not keep the Mac online without a `claude remote-control` process. The iOS Remote screen initially showed no devices because there was no interactive/server Claude process, despite the setting being enabled. An earlier `/rc active` and browser Connected check proved that one session worked at that time, not that a persistent host was available. A running `claude -p` job is also not the Remote Control host.

Availability was restored by starting `claude remote-control --name "Mac agents-setup" --capacity 1`, then stopping that foreground process cleanly before bootstrapping the login-scoped LaunchAgent at `/Users/gotasasaki/Library/LaunchAgents/local.claude.remote-control.plist`. Its verified command is `/Users/gotasasaki/.local/bin/claude remote-control --name "Mac agents-setup" --spawn=worktree --capacity 4`; it uses `RunAtLoad`, `KeepAlive`, and a 30-second throttle. `launchctl print "gui/$(id -u)/local.claude.remote-control"` reported running, one run, and no exit; Desktop's **Code > Local > Remote Control** showed `agents-setup` on `Mac-Mini-M6`. Logs are under `/Users/gotasasaki/.claude/remote-control/`. This is an idle server needed for remote reachability, distinct from autonomous agent-loop services, and it requires the Mac user to stay logged in with network access. The user has not yet confirmed device discovery or connection in iOS, so that outcome remains unverified.
