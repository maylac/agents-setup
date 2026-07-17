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

**Codex posture** (updated 2026-07-18): Codex runs with `approval_policy = "on-request"` and `sandbox_mode = "workspace-write"` (see `~/.codex/config.toml`) — the same approval design as Claude's auto mode: proceed inside the sandbox automatically, escalate to the human only when needed. Approval waits reach the phone via the PermissionRequest hook (`notify-mobile.sh approval Codex`). The sandbox stays on — the user explicitly rejected `danger-full-access` in 2026-07. Unattended delegation does not stall: `codex exec` has no approval flag at all, so non-interactive runs stay inside the sandbox and escalation-needing operations fail fast back to the model. Do not change either value without fresh user approval.

Full-auto does not mean irreversible: destructive operations, lockfile deletion, force push, publish/upload/send/archive, and payments/trading/account actions still require explicit user request or confirmation. Prefer draft/dry-run first and report commands/actions plus relevant output.

## TodoWrite

Use TodoWrite for multi-step tasks where progress tracking helps the user steer the work. Skip it for one-step edits or quick answers.

A useful task list exposes:
- out-of-order steps
- missing items
- unnecessary work
- wrong granularity
- misunderstood requirements
