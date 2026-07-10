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

**Codex exception**: Codex is intentionally run with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"` (see `~/.codex/config.toml`). This is a deliberate, user-approved exception to the rule above, not an oversight — do not "fix" it back to a restrictive policy.

Full-auto does not mean irreversible: destructive operations, lockfile deletion, force push, publish/upload/send/archive, and payments/trading/account actions still require explicit user request or confirmation. Prefer draft/dry-run first and report commands/actions plus relevant output.

## TodoWrite

Use TodoWrite for multi-step tasks where progress tracking helps the user steer the work. Skip it for one-step edits or quick answers.

A useful task list exposes:
- out-of-order steps
- missing items
- unnecessary work
- wrong granularity
- misunderstood requirements
