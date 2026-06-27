---
paths:
  - "**/*.{js,jsx,ts,tsx,mjs,cjs,py,go,rs,java,kt,kts,swift,c,cc,cpp,h,hpp,cs,php,rb,scala,dart,sql,sh,bash,zsh,fish,html,css,scss,json,yaml,yml,toml,xml}"
description: Code style preferences for files that are actually being edited or reviewed.
---

# Coding Style

Match the existing style of the project first.

## Data Updates

Prefer immutable updates for shared state, UI state, and data transformations when that matches the language and local code. Do not force immutable style into existing imperative code, performance-sensitive paths, or APIs whose normal use is mutation.

## File Organization

Keep files focused and cohesive. Extract helpers only when it reduces real complexity or meaningful duplication; do not split files just to satisfy a line-count target.

## Error Handling

Handle errors at the boundary where useful action can be taken. Surface user-facing messages in UI code, log useful context server-side, and avoid silently swallowing failures.

## Input Validation

Validate untrusted input at system boundaries. Prefer existing schema or validation helpers in the project over new one-off validation layers.

## Completion Check

Before marking code work complete, confirm the relevant checks for this change:
- readable names and local style
- focused functions and modules
- clear handling of realistic failure paths
- no unexplained hardcoded secrets or magic values
- no broad refactors unrelated to the request
