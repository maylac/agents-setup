---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Kotlin-specific content.

## Project Judgment Calls

- Prefer `val` over `var`; use `data class` and immutable collections in public APIs.
- Never use `!!` — prefer `?.`, `?:`, `requireNotNull()`, or `checkNotNull()`.
- Use sealed classes/interfaces for closed state hierarchies, with exhaustive `when` (no `else` branch).
- Use `Result<T>` or a sealed error type over exceptions for control flow; never swallow `CancellationException`.
- Keep extension functions discoverable (file named after the receiver type) and scoped — avoid extending `Any`.

## Reference

See skill: `kotlin-patterns` for comprehensive Kotlin idioms and code examples.
