---
paths:
  - "**/*.{js,jsx,ts,tsx,mjs,cjs,py,go,rs,java,kt,kts,swift,c,cc,cpp,h,hpp,cs,php,rb,scala,dart,sql,sh,bash,zsh,fish,html,css,scss,json,yaml,yml,toml,xml}"
description: Optional architecture patterns for implementation work; local project patterns take precedence.
---

# Common Patterns

Use local project patterns first. Only introduce one of these patterns when it clearly matches the existing codebase or removes real complexity.

## Skeleton Projects

For greenfield or large standalone functionality, it can be useful to inspect battle-tested skeleton projects or templates. Do this when starting from scratch would create unnecessary risk. Do not clone or port a template for a small feature that already fits the current project.

## Repository Pattern

Use a repository boundary when data access needs to be isolated from business logic, tested independently, or swapped across storage implementations. Do not add this abstraction for one-off CRUD code that the project already handles directly.

## API Response Format

Follow the API envelope already used by the project. If no convention exists, prefer a consistent shape with status, data, error details, and pagination metadata where relevant.
