---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Testing

> This file extends [common/testing.md](../common/testing.md) with Kotlin and Android/KMP-specific content.

## Project Judgment Calls

- Use `kotlin.test` for KMP-shared tests, JUnit 4/5 for Android-specific tests.
- Use **Turbine** for testing Flow/StateFlow, and `kotlinx-coroutines-test` (`runTest`, `TestDispatcher`) for coroutines.
- Prefer hand-written fakes over mocking frameworks for repositories and other collaborators.
- Use `Room.inMemoryDatabaseBuilder()` (Room) or `JdbcSqliteDriver(IN_MEMORY)` (SQLDelight) for database tests.
- Use backtick-quoted descriptive test names (`` `delete item emits updated list` ``).
