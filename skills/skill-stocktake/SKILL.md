---
name: skill-stocktake
description: Audit a canonical or installed skill collection for trigger quality, useful guidance, overlap, and working local dependencies. Use for skills only; use harness-audit for hooks, settings, MCP, or agents.
origin: ECC
---

# Skill Stocktake

Review the requested skill collection from its actual source of truth. Use a Quick Scan for changed skills when a compatible results cache exists; use a Full Stocktake when the cache is absent, stale for the target, or the user requests a full review.

## Locate the collection

Start by finding the canonical store and its mirrors. In the shared setup used here, the canonical store is `$HOME/.agents/skills`, while Claude and Codex directories are symlink mirrors. In another harness, inspect the active runtime rather than assuming these paths.

The bundled scripts accept a selected global root without modifying configuration:

```bash
STOCKTAKE_DIR="$HOME/.agents/skills/skill-stocktake"
SKILL_STOCKTAKE_GLOBAL_DIR="$HOME/.agents/skills" \
  bash "$STOCKTAKE_DIR/scripts/scan.sh"
```

Pass `SKILL_STOCKTAKE_PROJECT_DIR` when a project skill directory is explicitly in scope. The scripts require `bash`, `jq`, `find`, `awk`, and a platform-supported `date`; check them with `command -v` before relying on their output.

The results cache is `results.json` beside this skill in the selected collection. Treat a cache from another root or runtime as stale. Do not update it for an audit-only request, a partial independent review, or until the recorded evaluations are complete.

## Scan and evaluate

For every selected skill, verify before assigning a verdict:

- its `SKILL.md` frontmatter parses and its name matches the directory;
- its description is concise and routes the right requests;
- scripts, references, sibling skills, paths, CLIs, and configuration claims exist locally;
- instructions respect the active runtime and do not turn an example or old harness policy into a universal rule;
- actual overlap with global instructions or another skill is substantive.

Use `Keep`, `Improve`, `Update`, `Retire`, or `Merge into <target>`. Record self-contained evidence and a concrete repair for every verdict other than Keep. If tool-use counts are all zero, report telemetry as unavailable and judge from the artifacts.

Split a full review into coherent families only when parallel review is available and helps compare related skills. Persist completed evaluation data only after validating it. Do not force a subagent workflow for a small collection or a focused repair.

## Quick Scan

Run only when the cache refers to the same selected collection:

```bash
STOCKTAKE_DIR="$HOME/.agents/skills/skill-stocktake"
SKILL_STOCKTAKE_GLOBAL_DIR="$HOME/.agents/skills" \
  bash "$STOCKTAKE_DIR/scripts/quick-diff.sh" "$STOCKTAKE_DIR/results.json"
```

An empty array means no `SKILL.md` changed since the recorded evaluation. Warnings about missing cached files require a user decision before pruning them. To save completed results, pass validated JSON to `save-results.sh`; `--prune-missing` removes cache entries and requires explicit approval.

## Report and repair

Summarize the scope, scan evidence, per-skill verdicts, specific improvements, and residual issues. Make scoped content repairs that the request authorizes. Never delete, merge, archive, or overwrite a cache merely because the audit recommends it; first present the exact affected assets and reason.
