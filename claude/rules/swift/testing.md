---
paths:
  - "**/*.swift"
  - "**/Package.swift"
---
# Swift Testing

> This file extends [common/testing.md](../common/testing.md) with Swift specific content.

## Project Judgment Calls

- Use **Swift Testing** (`import Testing`, `@Test`/`#expect`) for new tests; migrate old XCTest files only when touching them anyway.
- Each test should get a fresh instance (set up in `init`, tear down in `deinit`) — avoid shared mutable state between tests.
- Use `@Test(arguments:)` for parameterized cases instead of hand-rolled loops.
- Coverage: `swift test --enable-code-coverage`, per the repository's own coverage target.
