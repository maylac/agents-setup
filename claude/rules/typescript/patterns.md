---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Patterns

> This file extends [common/patterns.md](../common/patterns.md) with TypeScript/JavaScript specific content.

## Project Judgment Calls

- Follow the project's existing API response envelope; if none exists, use a typed `ApiResponse<T>` shape with `success`/`data`/`error`/pagination `meta`.
- Extract a custom hook only when logic is reused across components, not for one-off effects.
- Use a `Repository<T>` interface only when data access must be swapped or tested independently of business logic.
