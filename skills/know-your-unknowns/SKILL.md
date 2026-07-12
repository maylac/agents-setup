---
name: know-your-unknowns
description: Surface blind spots via reviewable artifacts. Use when touching an unfamiliar module, when requirements are ambiguous inside an already-scoped task, when the user can't articulate the design they want, before porting a reference implementation, or before merging a skimmed diff. Not for routine implementation with clear requirements, and not for open-ended idea exploration (that's brainstorming).
---

# Know Your Unknowns

Prompting patterns for discovering what you don't know you don't know, so you can prompt better. Based on Thariq (@trq212, Anthropic Claude Code team)'s guide ["Know your unknowns"](https://thariqs.github.io/html-effectiveness/unknowns/): "The map is not the territory — the most important part of working with a capable model is discovering my own unknowns so I can prompt it better."

**Core idea:** Instead of asking the model to just *do* the work, first ask it to produce a **reviewable artifact** that externalizes the gaps in your understanding. React to the artifact, then prompt with what you learned. The original guide renders each artifact as a single self-contained HTML page; a well-structured markdown document works too — prefer HTML when interactivity (toggles, checklists, quizzes, variant switching) helps the human react.

**Boundary:** this skill is about *surfacing unknowns* through artifacts. For open-ended requirement/idea exploration use `superpowers:brainstorming`; for turning a settled spec into an implementation plan use `superpowers:writing-plans`. The dividing line for interview-style questioning: if the *shape of the deliverable itself* is undecided, that's brainstorming; if the task is approved and scoped but specific behaviors are ambiguous, that's pattern 6 here. `fable-escalation`'s desk-prep checklist delegates its blindspot/option-generation steps to patterns 1/3/5 of this skill.

## When to reach for which pattern

| Situation | Pattern |
|---|---|
| Touching a module you've never worked in | 1. Blindspot pass |
| Domain vocabulary you don't have | 2. Teach me my unknowns |
| Can't articulate the design you want | 3. Four design directions |
| UI/UX decisions before touching real code | 4. Mock before you wire |
| Committed to a fix before seeing alternatives | 5. Brainstorm the intervention |
| Requirements are ambiguous | 6. The interview |
| An existing implementation encodes the behavior you want | 7. Point at a reference |
| Plan review wastes your attention on mechanical steps | 8. The tweakable plan |
| Mid-build surprises vanish into the scrollback | 9. Implementation notes |
| Work is done but stakeholders aren't convinced | 10. The buy-in doc |
| About to merge a diff you only skimmed | 11. Quiz me before I merge |

## Phase 1 — Pre-implementation (patterns 1–8)

### 1. Blindspot pass
> "I'm adding a new SSO auth provider to Acme but I've never touched the auth module. Do a blindspot pass: find my unknown unknowns in this part of the codebase, explain each one, and tell me how to prompt you better for the implementation."

Artifact: cards categorized as **Landmine / History / Convention / Missing concept**, each with an explanation, a "Why it bites" callout, and a copyable corrective prompt chip. Ends with a single **improved prompt** that folds in every constraint plus an explicit work order ("Stop and show me the plan after X before writing code").

### 2. Teach me my unknowns
> "I don't know what color grading is but I need to grade the Acme launch video. Teach me color grading well enough that I understand my unknown unknowns and can prompt you with real vocabulary."

Artifact: a domain crash course (interactive where it helps) ending with **example prompts a professional would write** — the goal is vocabulary, not mastery.

### 3. Four design directions
> "I want a review-queue dashboard for Acme but I have no visual taste and don't know what's possible. Make me one HTML page with 4 wildly different design directions so I can react to them."

Artifact: the **identical dataset** rendered under 4 incompatible design philosophies, with steal/skip chips per direction that assemble a reply. Reacting is easier than imagining.

### 4. Mock before you wire
> "Before wiring anything up, make a single HTML file mocking Acme's new frame-annotation toolbar with fake data. I want to react to the layout before you touch the real app."

Artifact: a clickable throwaway mock with fake data and layout variants — you find out what you actually want the moment you can click it, not three PRs later.

### 5. Brainstorm the intervention
> "Here's my rough problem: Acme users churn after onboarding. Search the codebase and brainstorm 10 places we could intervene, from cheapest to most ambitious. I'll tell you which ones resonate."

Artifact: an option spectrum ("ship this afternoon" → "quarter-long bet") **grounded in what actually exists in the code**, with checkboxes that assemble a reply. Often reveals existing machinery that only needs wiring.

### 6. The interview
> "Interview me one question at a time about anything still ambiguous in the annotation-export feature. Prioritize questions where my answer would change the architecture."

One question at a time, **ordered by blast radius** — how much each answer would change the architecture.

### 7. Point at a reference
> "This Rust crate in vendor/rate-limiter implements the exact backoff behavior I want. Read it and reimplement the same semantics in our TypeScript API client — but first show me a semantics map so I can confirm you understood it."

Artifact: a **semantics map** of the reference (states, invariants, edge cases → target-language equivalents), marked "awaiting confirmation". Make the model prove it understood the reference before porting a single line.

### 8. The tweakable plan
> "Write an implementation plan for annotation export as HTML, but lead with the decisions I'm most likely to tweak: data model changes, new type interfaces, and anything user-facing. Bury the mechanical refactoring at the bottom — I trust you on that part."

Sort the plan by **likelihood you'll change it**, not by execution order — decisions worth your attention surface first; mechanical work sinks to the bottom.

## Phase 2 — During implementation (pattern 9)

### 9. Implementation notes
> "Keep an implementation-notes file as you build the export feature. If you hit an edge case that forces you to deviate from the plan, pick the conservative option, log it under 'Deviations', and keep going."

"Pick the conservative option and keep going" applies only to reversible deviations that don't change external behavior or contracts; for anything irreversible or user-visible, stop and ask instead of logging.

A running file (e.g. `docs/notes/<feature>-implementation.md`) where every deviation from the plan is logged as it happens — surprises become inputs to your next attempt instead of vanishing into the scrollback.

## Phase 3 — Post-implementation (patterns 10–11)

### 10. The buy-in doc
> "Package the prototype, the spec, and the implementation notes into a single doc I can drop in Slack to get buy-in on shipping annotation export. Lead with the demo."

The last unknown is **other people**. One skimmable doc (≈90-second read) that leads with the demo and answers objections before they're raised.

### 11. Quiz me before I merge
> "I want to make sure I understand everything that happened in this change before I merge. Give me an HTML report on the export-feature diff — context, intuition, what was done — with a quiz at the bottom that I must pass."

Artifact: a merge-readiness report (context / intuition / what was done) with a **quiz you must pass**. Turns "I skimmed the diff" into verified understanding — the artifact won't let you feel done until you actually are.

## Applying these patterns as the agent

When the user invokes this skill (or a prompt clearly matches one of the situations above):

1. Identify the phase and pattern; say which one you're using.
2. Substitute the user's actual project/module/feature into the template prompt.
3. Produce the artifact **before** doing the main work. Default to markdown; produce a single self-contained HTML file when interactivity materially helps (design directions, mocks, quizzes) or when the user asks.
4. End every pre-implementation artifact the way pattern 1 does: with a concrete **improved prompt** the user can fire next, including an explicit work order and stop points.
5. For Phase 1 (patterns 1–8): wait for the user's reaction before proceeding to implementation. Pattern 9 logs and keeps going (see its reversibility rule); Phase 3 artifacts are deliverables — produce and hand over, nothing to wait for.
