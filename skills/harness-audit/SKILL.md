---
name: harness-audit
description: Audit an agent harness across its installed skills, hooks, settings, MCP, agents, and memory. Use for cross-cutting setup failures, broken dependencies, or context cost; use skill-stocktake for skills only.
---

# Harness Audit

Audit a configured harness from its real installation, then produce an evidence-backed fix brief. Select only the asset families relevant to the request; a skills-only review belongs to `skill-stocktake`.

## Establish the target

1. Identify the requested runtime and its active home or canonical store. Do not assume a Claude, Codex, or another runtime path.
2. Locate its configuration files and follow symlinks before editing or reporting ownership.
3. Record the target paths, discovered runtime version where material, and unavailable tools. An absent optional integration is evidence, not a reason to install it.

For each in-scope asset, verify claims against the filesystem and available commands:

| Claim | Check |
|---|---|
| Script, reference, or asset exists | `test -e` / `test -x` |
| CLI or service is required | `command -v` and its local configuration |
| Symlink or mirror works | `readlink` plus target existence |
| Hook, MCP, agent, or scheduled job is registered | read the active config and inspect the referenced target |
| Version-sensitive behavior | verify the installed version or authoritative local documentation |

Read prose only after these checks. Treat zero-valued usage telemetry as unavailable when all assets show zero.

## Evaluate

Assess each asset on three axes:

- **Context cost:** concise, discriminating descriptions; instructions worth loading; conditional detail in references when it is substantial.
- **Task value:** trigger and scope match; guidance changes a decision beyond model baseline behavior; no overlap that merely restates global rules.
- **Runtime stability:** dependencies exist, paths match the chosen harness, and safety or authorization boundaries still hold.

Use `Keep`, `Improve`, `Update`, `Retire`, or `Merge into <target>`. Every non-keep verdict must cite the asset section and observed evidence. Never infer that a whole asset is broken from an unavailable optional integration.

## Deliverable and changes

Write a concise fix brief with:

- audited paths and evidence date;
- per-asset verdict, evidence, concrete repair, and residual risk;
- cross-cutting causes such as stale paths or description bloat;
- instructions anchored to headings rather than fragile line numbers.

Make justified repairs within the user's scope. Preserve canonical sources and symlink topology. Present deletions, merges, publishing, or changes outside the authorized harness scope for explicit user approval. A task authorization covers normal scoped repairs; do not ask again merely because a repair is reversible.

Re-run the checks affected by each repair and report the result. Update an audit cache only when this workflow produced the cache's stated evaluation; do not overwrite an unrelated or stale cache with partial results.
