---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with TypeScript/JavaScript specific content.

## Project Judgment Calls

- Add explicit types to exported functions, shared models, and component props; let TypeScript infer obvious local variable types.
- Prefer `unknown` over `any` for external/untrusted input, then narrow it.
- Use `interface` for object shapes that may be extended; use `type` for unions, intersections, and mapped types.
- In `.js`/`.jsx` files, use JSDoc types only when a TypeScript migration isn't practical.
- No `console.log` in production code — use the project's logging library.

## Reference

See skill: `coding-standards` for comprehensive TypeScript/JavaScript/React/Node idioms and code examples.
