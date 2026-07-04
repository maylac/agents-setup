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

## Troubleshooting Test Failures

When tests fail, check isolation, fixtures, mocks, and assumptions before changing production code. Fix the implementation unless the test is demonstrably wrong or stale.

Use `planner` when a test-first loop or tricky regression needs a focused plan before edits.
