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

Code work may be called complete only when every applicable line below passes. Each line is pass/fail — if it cannot be demonstrated, it fails:

- Names: a reader can predict what each new function or variable does without opening its body; no new abbreviation that doesn't already appear in the repo.
- Scope: every hunk in the diff traces back to the request; a hunk that would make a reviewer ask "why is this here?" fails this line.
- Failure paths: every new I/O, parse, or external call either handles failure or deliberately propagates it, and at least one realistic failure path was actually exercised (test or manual run), not just written.
- Magic values: every literal that isn't self-explanatory is named or carries a comment stating the constraint it encodes.
- Proof: "it works" is backed by pasted output (test run, log, or behavior diff) in the completion report. A description of what should happen is not proof.
