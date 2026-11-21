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

Follow `~/AGENTS.md` for shared approval rules and irreversible external side effects. Preserve existing local permission and hook configuration unless the user asks to change it.

Use `~/AGENTS.md` as the single source for effect-based authorization and hard stops. Tool-specific rules may narrow that policy but cannot widen it; follow concrete task and repository restrictions, and preserve system/runtime controls.

## TodoWrite

Use TodoWrite for multi-step tasks where progress tracking helps the user steer the work. Skip it for one-step edits or quick answers.

A useful task list exposes:
- out-of-order steps
- missing items
- unnecessary work
- wrong granularity
- misunderstood requirements
