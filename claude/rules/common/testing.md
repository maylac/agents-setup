---
paths:
  - "**/*.{js,jsx,ts,tsx,mjs,cjs,py,go,rs,java,kt,kts,swift,c,cc,cpp,h,hpp,cs,php,rb,scala,dart}"
  - "**/{test,tests,spec,specs,__tests__}/**/*"
  - "**/*.{test,spec}.{js,jsx,ts,tsx,mjs,cjs,py,go,rs,java,kt,kts,swift,c,cc,cpp,h,hpp,cs,php,rb,scala,dart}"
description: Testing guidance for code changes, scaled to risk and repository conventions.
---

# Testing Requirements

Use the repository's existing test strategy and coverage targets. Do not impose a global fixed coverage percentage unless the project already has that bar.

## Test Scope

Choose tests proportional to the change:
- bug fix: prefer a regression test that proves the bug is fixed
- new behavior: add or update the narrowest test that proves the requested behavior
- refactor: run existing tests that cover the changed behavior
- docs or config-only changes: use syntax, lint, or smoke checks when applicable

## TDD

Use test-first development when it clarifies the work or prevents regression. It is strongly useful for bug fixes and behavior changes, but it is not mandatory for every edit.

## Acceptance Bar (checkable)

A tested change passes this bar only if all applicable lines hold:

- bug fix: the regression test demonstrably fails on the pre-fix code, and the report states how that was checked (stash/revert run, or explicit reasoning when impractical)
- new behavior: the test name states the behavior ("rejects expired token"), not the mechanism ("calls validate()")
- the completion report contains the pasted test command and its output — the bare claim "tests pass" fails this line
- no test was weakened to go green (assertion removed or loosened, test skipped); if one was, that fact is the headline of the report, not a footnote

## Troubleshooting Test Failures

When tests fail, check isolation, fixtures, mocks, and assumptions before changing production code. Fix the implementation unless the test is demonstrably wrong or stale.

Use `planner` when a test-first loop or tricky regression needs a focused plan before edits.
