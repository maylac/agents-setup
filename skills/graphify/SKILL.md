---
name: graphify
description: Build or operate a persistent knowledge graph for a folder of code or content. Use for explicit graph creation, graph queries, or known-symbol relationship tracing; do not use for ordinary codebase search.
---

# Graphify

Build a queryable graph for code, documents, papers, images, or video. The durable outputs live in `graphify-out/`: `graph.json`, `GRAPH_REPORT.md`, and (by default) `graph.html`.

## Route the request

Start ordinary codebase discovery with `rg`. When a known symbol needs relationship context, and an existing `graphify-out/graph.json` plus a working graphify CLI or module is available, run `graphify explain "<symbol>"`; use `graphify path` only for two resolved symbols. If the graph runtime is unavailable, inspect the source with `rg` and report that graph evidence could not be checked. Do not treat every architecture or codebase question as a graph query: the graph is AST-only for code and can be stale or incomplete. Refresh it when source is newer than `graph.json` or `graphify-out/needs_update` exists.

| Request | Action | Read only when needed |
| --- | --- | --- |
| `/graphify --help` | Print the command list in [build.md](references/build.md#commands) and stop. | `build.md` |
| Explicit build, a path, or GitHub URL | Run the full build flow. | [build.md](references/build.md) |
| Existing graph plus a question | Check graph freshness; use `explain` for a known symbol, otherwise `query`. | [query.md](references/query.md) |
| `--update` or `--cluster-only` | Run the incremental or reclustering flow. | [update.md](references/update.md) |
| `add <url>` or `--watch` | Ingest or watch a corpus. | [add-watch.md](references/add-watch.md) |
| GitHub URL or several roots | Clone or merge before building. | [github-and-merge.md](references/github-and-merge.md) |
| Extra export, MCP, or benchmark | Run only the requested export. | [exports.md](references/exports.md) |
| Commit hook or project instruction integration | Install or inspect that integration. | [hooks.md](references/hooks.md) |

## Shared rules

- Before every graph operation, verify either `graphify` on `PATH` or `graphify` importable through the recorded interpreter. Only an explicitly requested build may install or set up graphify; a relationship query falls back to source inspection when unavailable.
- Graphify needs no API key. Code extraction is deterministic; semantic extraction may use an already configured Gemini key, otherwise use the host model. Never request an unrelated provider key.
- Preserve evidence: do not invent edges; mark uncertainty `AMBIGUOUS`; report skipped sensitive files, corpus-size warnings, and token cost.
- Treat graph output as evidence with coverage limits. Cite source locations when answering from it.
- Do not write or replace project instructions, hooks, database exports, or remote graph targets unless the user requested that operation.

## Build outcome

For a successful build, give a concise corpus summary and point to the generated artifacts. Surface only the most useful report findings and offer one grounded follow-up question. The detailed extraction, merge, health-check, labeling, export, cleanup, and report sequence is in [build.md](references/build.md).
