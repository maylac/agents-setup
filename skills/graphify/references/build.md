# Graphify build flow

Load this only for an explicit build or `/graphify --help`.

## Commands

```text
/graphify [path] [--mode deep] [--update] [--cluster-only] [--directed]
           [--no-viz] [--obsidian] [--svg] [--graphml] [--wiki]
           [--neo4j | --neo4j-push URI] [--falkordb | --falkordb-push URI]
           [--mcp] [--watch]
/graphify add <url> [--author NAME] [--contributor NAME]
/graphify query "question" [--dfs] [--budget N]
/graphify path "symbol A" "symbol B"
/graphify explain "symbol"
```

Use `.` when no path is supplied. A GitHub URL or multiple roots uses [github-and-merge.md](github-and-merge.md) first. `--update`, `--cluster-only`, `add`, `--watch`, and optional exports have their own routed references; do not run them as part of a normal build.

## 1. Preflight and corpus

Resolve an interpreter that can import `graphify`; prefer the interpreter recorded in the `graphify` executable's shebang, then `python3`. If the package is absent, an explicit build may install `graphifyy` with `uv tool install --upgrade graphifyy` when `uv` is present, otherwise install into an isolated venv. Record the resolved executable path in `graphify-out/.graphify_python` and the absolute input root in `graphify-out/.graphify_root`. Run the preserved commands in [build-full.md](build-full.md) for this preflight and each build phase.

Run `graphify.detect.detect(Path(input_path))`, writing `graphify-out/.graphify_detect.json`. Summarize supported files and words without dumping the JSON. Stop on an empty corpus. Always name skipped sensitive files.

When the corpus exceeds 2,000,000 words or 500 files, show the five largest first-level folders and ask the user to narrow it. If every file is at the root, suggest `--no-cluster` and continue. For video or audio, read [transcribe.md](transcribe.md) before extraction.

## 2. Extract in parallel

Code uses deterministic AST extraction. Run it for detected code files and write `graphify-out/.graphify_ast.json` with the supplied command.

Documents, papers, and images use semantic extraction. A code-only corpus writes an empty semantic result and skips this branch. If `GEMINI_API_KEY` or `GOOGLE_API_KEY` already exists, use the Gemini corpus extractor; otherwise extract with the host model. Never stop for or ask for any API key. For semantic chunks, load [extraction-spec.md](extraction-spec.md) and follow its schema, deterministic IDs, evidence labels, and output-path rules exactly. Write each chunk result and merge valid chunks into `graphify-out/.graphify_semantic.json`.

If an extraction chunk fails, report it and leave its files unstamped so a later update retries them. Do not merge stale semantic output.

## 3. Merge, build, and check

Merge AST and semantic fragments with the graphify library, preserving absolute source paths until the build relativizes them against the input root. Guard before writing: an empty extraction must never replace an existing graph or report. Use the supplied merge and build commands rather than reimplementing the module calls.

Build the graph, communities, analysis, questions, JSON, report, and HTML. Honor the library's shrink guard: if JSON was not written because it would shrink an existing graph, do not replace the report or analysis sidecar. Run the health check; report invalid edges, dangling nodes, or suspiciously low coverage rather than masking them. Label communities only from observed content.

Generate Obsidian output only with `--obsidian`. Read [exports.md](exports.md) for each requested extra export. Save a portable manifest and semantic hashes only for files that produced output, then clean temporary chunks. Keep raw corpus entries in the manifest so exclusions do not masquerade as deletions.

## 4. Report

State the absolute artifact directory, graph size, community count, extraction coverage, and token cost. Link or name `graph.html`, `GRAPH_REPORT.md`, and `graph.json`; quote only the report's God Nodes, Surprising Connections, and Suggested Questions sections. Offer the most informative suggested question for a follow-up traversal.
