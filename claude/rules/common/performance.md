---
paths:
  - "**/.claude/**"
  - "**/.codex/**"
  - "**/AGENTS.md"
  - "**/CLAUDE.md"
description: Context, model, and troubleshooting guidance that should stay conditional and current-state based.
---

# Performance And Context

## Model Selection

Use medium effort by default, high for difficult design, debugging, or material-risk review, and xhigh only for exceptional tasks with a clear reason. Use lighter settings for quick, low-risk work. Prefer focused reads and deterministic checks; stop when relevant acceptance criteria pass and rerun broad checks only after a change, failure, or specific unresolved risk.

Use the model and thinking settings currently available in the user's Claude Code configuration. Do not rely on hardcoded model names in this file as proof that a model is available.

Choose lighter settings for quick edits, status checks, and low-risk docs work. Use stronger reasoning for architecture, ambiguous debugging, security-sensitive work, or large multi-file changes.

## Context Window Management

Avoid starting large refactors, broad debugging, or multi-file features in the last 20% of the context window. Single-file edits, simple docs updates, and narrow bug fixes can tolerate higher context usage if the relevant facts are already present.

## Plan Mode

Use plan mode for ambiguous requirements, architectural work, or decisions that need user review before edits. For ordinary multi-step work, state a brief plan and proceed. Do not require plan mode for straightforward local changes. If execution goes sideways mid-plan, stop and re-plan rather than pushing through.

## Build Troubleshooting

If a build fails, read the error first, inspect the relevant files, fix incrementally, and verify after each change. Use a build resolver agent when the error is broad, language-specific, or not obvious from the immediate output.
