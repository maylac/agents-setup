---
name: apple-design
description: Design responsive interfaces and interactions with Apple-style direct manipulation, interruptible motion, material hierarchy, and accessibility. Use for interaction or visual design work where those qualities are requested.
---

# Apple Design

Build interfaces that react immediately, keep the user in control, and communicate hierarchy through motion, type, and materials.

## Choose the relevant guidance

| Work | Apply | Read only when needed |
| --- | --- | --- |
| Gesture, sheet, carousel, drag, or snap behavior | Track input directly and hand momentum into an interruptible spring. | [gestures.md](references/gestures.md) |
| General UI transitions | Use a restrained, interruptible spring from the current presentation value. | [motion.md](references/motion.md) |
| Toolbar, sheet, modal, typography, accessibility, or feedback | Make hierarchy legible and preserve equivalent non-vestibular feedback. | [interface-craft.md](references/interface-craft.md) |

## Core decisions

- Respond on input, not after it. A drag tracks 1:1 from the user's grab point; a tap visibly acknowledges touch-down.
- Let users redirect a moving element at any moment. Do not lock input during transitions or restart an animation from its stale target.
- Use critically damped springs for ordinary UI. Reserve slight bounce for a release that carried physical momentum.
- Keep a spatial relationship with the initiating control: shared origin, symmetric entry and exit path, and intent visible during travel.
- Prefer direct labels, clear wayfinding, and one primary task over decorative motion or surface effects.
- Respect reduced motion, reduced transparency, contrast preferences, text scaling, keyboard focus, and touch target size.

## Verify

Test the actual interaction: grab a moving element midflight, reverse it, release with different velocities, and check the reduced-motion equivalent. Review large text, modal focus, and translucent surfaces against their changing backgrounds.
