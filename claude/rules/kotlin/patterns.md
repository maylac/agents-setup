---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Patterns

> This file extends [common/patterns.md](../common/patterns.md) with Kotlin and Android/KMP-specific content.

## Project Judgment Calls

- Prefer constructor injection; use Koin (KMP) or Hilt (Android-only) — match whatever the project already uses.
- ViewModels: single state object, event sink, one-way data flow (`MutableStateFlow` + `asStateFlow()`).
- Repositories: `suspend` functions return `Result<T>` (or a custom error type), `Flow` for reactive streams.
- UseCases: single responsibility, `operator fun invoke`.
- Use `expect`/`actual` only for genuine platform-specific implementations in KMP code.

## Reference

See skill: `kotlin-coroutines-flows` for coroutine/Flow patterns and `android-clean-architecture` for module and layer patterns.
