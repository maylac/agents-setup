---
name: autonomous-team
description: Run a bounded Claude Code team task with isolated worker ownership, checked acceptance evidence, and a review bound to the exact integrated workspace snapshot.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: 'python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" hook-pre'
          timeout: 2
  Stop:
    - hooks:
        - type: command
          command: 'python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" hook-stop'
          timeout: 10
---

# Autonomous Team

Use for one bounded task in a Claude conversation that benefits from a
Claude Code worker in an isolated Git worktree. This skill's hooks are scoped
to sessions where the skill is active. They do not modify user settings or weaken the current
permission mode, sandbox, or tool restrictions.

## Contract and execution

1. Before dispatch, write a small DAG contract with the objective, exact owned
   paths, acceptance commands for each node, dependency edges, the full base
   commit SHA, and the required outcome. Split only independent, bounded work.
   Use exactly one gated task per Claude conversation. Invoke this skill, then
   initialize the gate immediately with that conversation's native session ID,
   before starting workers:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" init \
     --session "${CLAUDE_SESSION_ID}" \
     --cwd "$PWD" \
     --base-sha "$(git rev-parse HEAD)" \
     --owned-path src/module.py \
     --owned-path tests/test_module.py \
     --check 'python -m pytest tests/test_module.py'
   ```

   The base SHA must be the commit the worker was asked to use. The helper
   checks that it matches the coordinator checkout at initialization. Claude's
   native isolated worktree starts from the default branch, so use it only when
   that branch is the intended base. The worker must check `git rev-parse HEAD`
   against the pinned SHA before editing and stop on any mismatch. For a task
   based on another branch, create a dedicated worktree at that exact SHA and
   launch a normal bounded Claude process there. Do not use `team-worker` with
   native worktree isolation for this case because it starts from the default
   branch again.
2. Dispatch one bounded task to `team-worker`, setting its `owned_paths`,
   `base_sha`, and acceptance criteria explicitly. Ask it to report the base
   SHA it used, changed paths, commands and results, and any blocker. Do not
   let it create more agents. The main agent checks the worker's base and
   diff, integrates only contract paths, and confirms that no unrelated dirty
   work was included.
3. Run the acceptance commands from the coordinator's Bash context after
   integration. This is the only command that executes those checks and it
   records their result against a hash of the current workspace:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" check \
     --session "${CLAUDE_SESSION_ID}" --cwd "$PWD"
   ```

   Do not ask a hook to run commands. Inspect the actual worker diff and have
   `code-reviewer` review that integrated diff read-only. Copy its concise
   report to a review evidence file outside the checkout. Before review, ask
   the reviewer to include the exact line `Snapshot: <HASH>` in its report,
   where `<HASH>` is copied from this command:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" snapshot \
     --session "${CLAUDE_SESSION_ID}" --cwd "$PWD"
   ```

   Bind the report to that same snapshot:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" review \
     --session "${CLAUDE_SESSION_ID}" --cwd "$PWD" \
     --outcome pass --evidence /path/to/review.md --snapshot <HASH>
   ```

4. Retry only failed DAG nodes and nodes that depend on them. A failed node may
   have at most two implementation approaches; stop and record `blocked` after
   the second failed approach. Do not repeat successful nodes. If a failure
   reveals a verified, reusable root cause, record it through the shared
   `extract-approach` skill.
5. Finish with `ready` only after checks and review pass on the current exact
   snapshot:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" finish \
     --session "${CLAUDE_SESSION_ID}" --cwd "$PWD" --outcome ready
   ```

   For an unresolved failure or a human-only action, record the actual terminal
   state and reason instead:

   ```bash
   python3 "$HOME/.claude/skills/autonomous-team/scripts/team_gate.py" finish \
     --session "${CLAUDE_SESSION_ID}" --cwd "$PWD" \
     --outcome approval-required --reason 'Production release requires owner approval'
   ```

   `blocked` and `approval-required` are valid reported outcomes, not success.
   Do not merge a PR, deploy, publish, or perform another hard-stop action
   without the required approval. A reviewer finding is not a passing review.

## Gate behavior and limits

- State lives under the Git common directory in `team-runs/autonomous-team/`,
  outside the worktree, and is separated by session ID and checkout path.
- The stop hook never runs contract commands. It verifies owned paths, fresh
  check receipts, unchanged review evidence, and snapshot hashes. It blocks an
  incomplete session at most twice; afterward it allows stopping and emits a
  system message that says the result is unverified. This message does not
  guarantee the final report is truthful. Corrupt state is blocked once, then
  receives the same diagnostic. Hooks silently skip sessions outside Git and
  other worktrees that share the same Git metadata.
- Use a trailing slash for an owned directory (for example `src/module/`).
  Submodule contents are outside the snapshot and ownership check; only the
  parent repository's gitlink revision is tracked.
- Pre-existing unrelated dirty paths are recorded as a baseline and must keep
  their exact contents and Git status throughout the task. Pre-existing dirty
  owned paths cause initialization to stop. New out-of-scope edits, including
  non-ignored untracked files, block acceptance. Ignored files are outside the
  snapshot and scope check.
- Acceptance command output is retained in a bounded log beside the session
  state under Git metadata; failures also print the last 4,096 characters of
  stdout and stderr. Hooks never execute these commands.
- The Bash hook asks for approval before common high-risk commands such as a
  force push, history rewrite, default-branch merge, PR merge, deploy, or
  publish. Pattern matching is a convenience prompt, not a security boundary;
  normal tool permissions and sandbox rules remain authoritative.
- Without initialized state, the Stop hook is inactive; the Bash hook still
  asks before recognized high-risk commands while this skill is active. Use a
  new session ID per task to avoid stale evidence.

## Codex use

The same skill is shared with Codex. The Claude frontmatter hooks and
`${CLAUDE_SESSION_ID}` are Claude-only. For Codex, choose a safe explicit ID
for one task (for example `codex-2026-11-03-a1b2c3d4`) and use the shared path:

```bash
GATE="$HOME/.agents/skills/autonomous-team/scripts/team_gate.py"
SESSION="codex-2026-11-03-a1b2c3d4"
python3 "$GATE" init --session "$SESSION" --cwd "$PWD" \
  --base-sha "$(git rev-parse HEAD)" --owned-path src/module.py \
  --check 'python -m pytest tests/test_module.py'
```

Codex should invoke `team_gate.py` directly for `check`, `snapshot`, `review`,
and `finish`, and use a native Codex worker with `gpt-6-luna` for bounded
implementation while the main `gpt-6-astra` session judges and integrates.
Keep the active sandbox and approval policy; never use bypass flags.
