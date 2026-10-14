---
name: stop-gate-review
description: Return an ALLOW/BLOCK review when explicitly asked to judge only the immediately previous Claude turn.
---

# Stop-Gate Review

## Core Rule

Review only the immediately previous Claude turn. Do not audit older turns, the whole branch, or unrelated repo state unless the previous turn's concrete edit requires that exact check.

The first line must be exactly one of:

```text
ALLOW: <short reason>
BLOCK: <short reason>
```

## Procedure

1. Determine whether the immediately previous Claude turn directly edited files or produced a code/config artifact.
2. If it was only status, setup reporting, command guidance, clarification, or other non-editing work, return `ALLOW:` immediately.
3. If it edited files, identify the likely target repo or file from that turn before searching broadly.
4. Inspect only the claimed files, diff, or logic first. Ground any `BLOCK:` in current-run evidence, not in the prior assistant's summary.
5. Challenge the edited work for practical ship risk: stale state, empty-state behavior, retries, convergence, rollback risk, path drift, and validation gaps.
6. Return the terse decision. Keep extra explanation short unless the user asked for more.

## Efficient Checks

- Start in the likely project path and run `git rev-parse --show-toplevel` if the root is uncertain.
- Use `git status --short`, `git diff --stat`, `git diff -- <file>`, `rg -n`, and focused source inspection before broad searches.
- For markdown rename or heading-only changes, a direct `diff -u old new` can be enough.
- For Python syntax checks under restricted locations, avoid treating `py_compile` cache-write failures as code defects; use another validation path.

## Pitfalls

- Do not keep investigating after confirming the previous turn was non-editing.
- Do not block based on an assistant claim that a file changed; inspect the file or diff.
- Do not turn the gate into a full code review unless the previous turn itself edited a broad surface.
- Do not include older Claude turns in scope, even if they are nearby in the transcript.

## Verification Checklist

- The previous turn was classified as editing or non-editing.
- Any `BLOCK:` cites current file, diff, or command evidence.
- The first line is exactly `ALLOW:` or `BLOCK:`.
- The answer remains scoped to the previous turn.
