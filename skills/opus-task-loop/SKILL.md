---
name: opus-task-loop
description: Apply a stop-or-continue verification loop after a failed approach, repeated tool failure, uncertain completion claim, or high-cost stopping decision. Do not trigger for ordinary multi-step work with clear acceptance criteria.
license: MIT
---

# Opus Task Loop

## Overview

Hard tasks fail less from lack of skill and more from silently skipping a step in the loop: **decompose → act → verify → decide next**. Tested against baseline behavior: without this discipline, time pressure alone is enough to collapse "verify" into "it ran without an error" and "decide next" into premature "done."

**Core principle:** every step needs an independent check, and "ran/looks fine" is not that check.

## The Loop

1. **Decompose** — surface every ambiguous point in the request before building anything. Don't silently pick a default for unspecified behavior (rounding, negative values, missing/empty input, edge categories) — name the decision out loud (in the response or a one-line comment) and pick data/tests that exercise exactly those points.
2. **Act** — do the smallest next step, not the whole task at once.
3. **Verify** — confirm the result a way that's independent of just running it (see below). If it reveals a bug, switch to superpowers:systematic-debugging for root cause rather than patching the symptom.
4. **Decide next** — only stop a step once it's actually verified; otherwise the next action is closing that gap, not moving on.

**REQUIRED SUB-SKILL:** superpowers:verification-before-completion is the hard gate before any "done"/"fixed"/"confirmed" claim — this loop is how you produce the evidence that gate demands, before you get there.

## Verify Means Independent, Not Cosmetic

"No traceback" and "output looks plausible" are not verification — they're the two things a model reaches for first under pressure, and both leave the actual numbers/logic unchecked.

| What you did | Is it verification? |
|---|---|
| Ran it, no crash | No — proves the code executes, not that it's correct |
| Eyeballed the output, looked right | No — plausible ≠ correct |
| Recomputed the expected result a different way (hand math, alt script) and diffed against actual | Yes |
| Actually ran the edge case you claim to handle (missing file, empty input, boundary value) | Yes |
| Assumed a `try/except` "handles" a path without ever triggering that path | No — untriggered code is unverified code |

## Deciding What's Next

After each step, before doing anything else:
1. Does the actual result match an independently-computed expected result, including the edge cases named during decomposition? If no → stay on this step.
2. Is there a gap between this result and the original ask? If yes → the next step closes that gap, not something new.

Only stop when both are satisfied.

| Pressure | Rationalization | Reality |
|---|---|---|
| "Quick, no time to be fancy" | "It ran, that's confirmed" | Running ≠ verified; say what's actually checked vs. assumed |
| Deadline in minutes | "I'll flag the edge case instead of testing it" | Fine to flag scope you're *not* doing — not fine to claim something *is* handled without triggering it |
| Happy path passed | "Good enough, ship it" | The edge cases you identified in decomposition are part of the ask, not optional polish |
| Tempted to add more | "While I'm here, let me also add X" | Not requested = flag it, don't build it (karpathy-guidelines: simplicity first) |
