---
paths:
  - "**/.claude/**"
  - "**/.codex/**"
  - "**/hooks/**"
description: Local Claude hook and task-tracking conventions.
---

# Hooks System

## Hook Types

- **PreToolUse**: validation or parameter checks before tool execution.
- **PostToolUse**: formatting, checks, or notifications after tool execution.
- **Stop**: final verification or reporting when a session ends.

## Auto-Accept Permissions

Use auto-accept only for trusted, well-defined work. Keep exploratory work explicit. Do not use dangerously-skip-permissions mode. Prefer durable allow rules in the relevant settings file when repeated permission prompts are expected.

**Codex posture** (updated 2026-07-20, user-approved): Codex runs with `approval_policy = "never"`, `sandbox_mode = "workspace-write"`, and `[sandbox_workspace_write] network_access = true` (see `~/.codex/config.toml`) — fully autonomous inside the sandbox, matching Claude/Hermes execution autonomy. No approval prompts: operations the sandbox blocks fail fast back to the model, which works around them. The sandbox stays on — the user explicitly rejected `danger-full-access` in 2026-07 and that rejection still stands. History: on-request (2026-07-18) → never (2026-07-20, user found repeated approvals inefficient). Do not change these values without fresh user approval.

Full-auto does not mean irreversible: destructive operations, lockfile deletion, force push, publish/upload/send/archive, and payments/trading/account actions still require explicit user request or confirmation. Prefer draft/dry-run first and report commands/actions plus relevant output.

## TodoWrite

Use TodoWrite for multi-step tasks where progress tracking helps the user steer the work. Skip it for one-step edits or quick answers.

A useful task list exposes:
- out-of-order steps
- missing items
- unnecessary work
- wrong granularity
- misunderstood requirements
