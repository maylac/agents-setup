---
name: hallmark
description: Design or improve a web page, page section, or component with a deliberate visual system. Use for requested UI builds, visual redesigns, audits, or design-DNA study; do not apply to routine implementation without a design request.
version: 1.1.0
---

# Hallmark

Create distinctive, usable interfaces without fabricated proof points or recycled page rhythms. Treat the user's product, content, and established design system as the source of truth.

## Route the request

| Request | Action | Read only when needed |
| --- | --- | --- |
| Build or visually improve a whole page | Run the page flow below. | Relevant references in [page-flow.md](references/page-flow.md) |
| A single interactive component | Use component scope. | [component-scope.md](references/component-scope.md) |
| `hallmark audit` | Inspect and return a ranked, non-mutating punch list. | [verbs/audit.md](references/verbs/audit.md) |
| `hallmark redesign` | Redesign within the named implementation boundaries. | [verbs/redesign.md](references/verbs/redesign.md) |
| `hallmark study <image or URL>` | Diagnose design DNA; never pixel-copy. | [study.md](references/study.md) |

If an attached image or URL has no verb, ask whether to study its DNA or use it as a reference for a fresh build. For an existing project, state the files you expect to change before editing. Do not delete production files, route trees, or component directories without explicit approval.

## Rules that always apply

- Preserve supplied facts, copy intent, brand, routes, and component ownership. Never invent metrics, logos, testimonials, or proof.
- Select tokens before implementation; reference named colour and font tokens in artifacts rather than improvising inline values.
- Do not draw fake browser, device, editor, or code-window chrome.
- Verify responsive behavior at 320, 375, 414, and 768 px: no horizontal scrolling, long-word wrapping, usable navigation, and visible focus.
- Keep display headings roman. Use weight, colour, or underline for emphasis rather than italic headings.
- Before handoff, score Philosophy, Hierarchy, Execution, Specificity, Restraint, and Variety. Revise any score below 3, then run the applicable slop-test gates.

## Page flow

1. Read the target's existing system first: `design.md`/`DESIGN.md`, fonts, palette, spacing, framework, and motion dependencies. A locked design file governs later choices. Read [page-flow.md](references/page-flow.md#preflight-and-context) for the cache, conflict, and user-context protocol.
2. Choose scope, genre, macrostructure, navigation, footer, and theme before code. Reuse a locked system; otherwise diversify from recent `.hallmark/log.json` entries. Read only the chosen genre, macrostructure, theme, and component recipes through [page-flow.md](references/page-flow.md#selection-and-loading).
3. Decide whether the hero needs enrichment. Typography-only is the default; load asset or craft guidance only when the brief needs it.
4. Give a compact preview of the selected structure, theme, sections, enrichment, motion, and diversification before emitting code.
5. Build with the project's conventions and named tokens. Stamp page CSS, append project memory, and preserve existing global stylesheet directives. The exact output and handoff rules are in [page-flow.md](references/page-flow.md#build-and-handoff).

## Detail routes

- Read [custom-theme.md](references/custom-theme.md) only for an explicit or clearly signalled custom theme.
- Read [hero-enrichment.md](references/hero-enrichment.md), [custom-craft.md](references/custom-craft.md), or [assets.md](references/assets.md) only for the selected enrichment route.
- Read [interaction-and-states.md](references/interaction-and-states.md) for stateful UI and [responsive.md](references/responsive.md) when mobile is in scope.
- Read [slop-test.md](references/slop-test.md) only after implementation, and [contract.md](references/contract.md) at handoff.
- Read [design-md.md](references/design-md.md) only when the user explicitly asks to lock or export the system.
