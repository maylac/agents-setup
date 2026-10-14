---
name: cross-harness-collab
description: Split normal actionable work with the other harness (Claude or Codex) by dispatching one bounded, owned-path work subtask, or get one read-only peer judgment. Use by default whenever a task admits a useful division; keep only tiny or indivisible tasks local.
---

# Cross-harness collaboration

Use this by default for normal actionable tasks that admit a useful division: assign at least one bounded subtask to the other harness while you advance an independent part. Do not wait for ambiguity, failures, or risky review; the priority is using both harnesses' available capacity to make progress, not minimizing invocations. Keep truly tiny or indivisible tasks and simple answers local. Honor explicit model choices and opt-outs.

The main session owns planning, integration, and final decisions. Within Codex, Luna executes and Astra judges; Claude execution defaults to Opus 5.5 at medium effort. Default to one external worker with explicit disjoint file ownership and acceptance checks. Do not duplicate work between owner and worker. Task authorization covers bounded local edits and tests, not unrelated external side effects.

## Modes

Run `scripts/consult.py` from this skill directory, selecting the other harness with `--target claude|codex` and `--cwd`. The brief is read from stdin; the helper prints one JSON receipt.

- `--mode work`: the worker may edit its assigned files and run scoped tests. Requires at least one `--owned-path` (repeatable, relative to `--cwd`). Defaults: Codex `gpt-6-luna` high (`workspace-write` sandbox), Claude `claude-opus-5-5` medium (Read/Glob/Grep/Edit/Write/Bash, `acceptEdits`, $5 budget); timeout 600 s.
- `--mode consult` (default, backward compatible): read-only judgment. Defaults: Codex `gpt-6-astra` low (`read-only` sandbox), Claude `claude-opus-5-5` medium (Read/Glob/Grep only, $1 budget); timeout 120 s. `--owned-path` is rejected.

`--model`/`--effort` overrides win. Missing CLIs, auth failures, or model errors are reported, never silently rerouted; if a route is unavailable, say so and continue authorized work locally without claiming the other harness participated. Both routes use the installed CLI and its existing auth. The Claude route runs in safe mode with no setting sources or session persistence; the Codex route ignores user config and rules, disables hooks, and sets `project_doc_max_bytes=0`. Codex resolves the CLI through symlinks and prepends the real executable's bundle directory to the child `PATH`, without changing global shell configuration. Put any needed repo rules in the brief.

## Briefs and ownership

Send the goal, acceptance checks, relevant paths or diff, applicable repo rules, and evidence. Omit the transcript and your preferred conclusion. For work, list the owned paths and say what others concurrently own.

Owned paths are a coordination contract stated in the prompt, not an OS per-file sandbox; the helper validates that they stay inside `--cwd` but does not enforce which files the worker edits. A work receipt with `status: "returned"` and `task_verified: false` records a response, not task success; the owner inspects artifacts and runs acceptance checks before reporting completion. Preflight errors set `partial_changes_possible: false`; failures after launch set it true, so inspect owned paths before retrying.

Workers and peers are marked (`CROSS_HARNESS_WORKER=1` / `CROSS_HARNESS_PEER=1`) and must not spawn peers, native agents, or another harness; the helper refuses nested calls.

## Bounds

Consultation: one pass, then at most one focused follow-up as a fresh session with a delta brief; then decide rather than looping for agreement. This is not a cap on actual work: the owner may issue further distinct scoped tasks or revisions when needed.

If an outer runner imposes a timeout, set it about 15 seconds longer than `--timeout` so the helper can stop and reap its child. `SIGKILL` cannot be intercepted, so avoid externally killing the helper. Treat session IDs and model self-statements as metadata; `model_verified: false` means serving identity is unverified (the current Codex JSON stream omits it).

## Examples

```sh
printf '%s\n' 'Goal: ...' 'Acceptance: ...' 'Others own: ...' | \
  python3 /path/to/cross-harness-collab/scripts/consult.py \
  --target codex --cwd /path/to/repo --mode work \
  --owned-path src/foo.py --owned-path tests/test_foo.py --timeout 900

printf '%s\n' 'Question: ...' 'Evidence: ...' | \
  python3 /path/to/cross-harness-collab/scripts/consult.py \
  --target codex --cwd /path/to/repo
```
