# Approval resumes must preserve the exact stopped execution state

- Date: 2026-11-01
- Area: agents-setup / slack-bridge
- Type: architecture

## Problem

An `APPROVED:` reply must authorize one action against the exact worktree where the bridge stopped. The bridge also needs to prevent a new issue from reusing those paths before the stopped issue finishes.

## Rejected approaches

- Recreate a clean worktree at resume time: that changes the target state the person approved.
- Put worktree metadata after agent output in the same comment: an output tail can contain control-looking text and obscure which fields the bridge wrote.
- Parse source comment text through a trimming contract parser: trailing newlines are part of the hashed source bytes and must survive attachment.

## Effective approach

Write an authenticated top-level `NEEDS-APPROVAL:` comment containing only the recorded worktree path and branch. Resume only after a later top-level approval from an explicitly configured login; validate path and branch within the same Git worktree record, remove approval labels before invoking the agent, and preserve the dirty worktree without fallback cleanup. Recheck current approval and completed-scope reservations while processing the poll, and append fetched source only after a canonical GitHub comment URL's SHA256 matches the exact UTF-8 body. Remove the bridge's `GH_TOKEN` from the child agent environment so only the bridge API process uses its configured identity.

## Why it works

The marker defines the temporal boundary for approval, the Git worktree record binds the authorized path to its branch, and poll-local reservations account for tasks that change state during the current pass. Keeping metadata separate from agent output prevents the output from manufacturing trusted resume coordinates. The fake-`gh` end-to-end test verified exact source bytes including trailing newlines, two distinct approval rounds, dirty worktree reuse, reapproval after a second stop, and same-poll duplicate rejection; the bridge/doctor suite passed 56 tests.

## General rule

When approval resumes a paused operation, persist the exact execution identity as trusted bridge metadata, bind it to the approver and the latest stop, and consume the approval before execution. Scope locks must be updated as soon as an operation pauses or completes.
