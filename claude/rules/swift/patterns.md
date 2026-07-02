---
paths:
  - "**/*.swift"
  - "**/Package.swift"
---
# Swift Patterns

> This file extends [common/patterns.md](../common/patterns.md) with Swift specific content.

## Project Judgment Calls

- Define small, focused protocols with protocol extensions for shared defaults; avoid one giant protocol per type.
- Use structs for data transfer objects and models; use enums with associated values to model distinct states.
- Use actors for shared mutable state instead of locks or dispatch queues.
- Inject protocols with default parameters (production uses the default, tests inject a mock) rather than a separate DI framework, unless the project already has one.
