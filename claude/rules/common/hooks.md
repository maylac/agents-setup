---
description: Local Claude hook and task-tracking conventions.
---

# Hooks System

## Hook Types

- **PreToolUse**: validation or parameter checks before tool execution.
- **PostToolUse**: formatting, checks, or notifications after tool execution.
- **Stop**: final verification or reporting when a session ends.

## Auto-Accept Permissions

Use auto-accept only for trusted, well-defined work. Keep exploratory work explicit. Do not use dangerously-skip-permissions mode. Prefer durable allow rules in the relevant settings file when repeated permission prompts are expected.

## TodoWrite

Use TodoWrite for multi-step tasks where progress tracking helps the user steer the work. Skip it for one-step edits or quick answers.

A useful task list exposes:
- out-of-order steps
- missing items
- unnecessary work
- wrong granularity
- misunderstood requirements
