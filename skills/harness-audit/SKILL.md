---
name: harness-audit
description: Audit an agent harness across skills, hooks, settings, MCP, agents, and memory for efficiency and stability. Use for cross-cutting setup audits, broken dependencies, or context bloat. For a skills-only rescan, use skill-stocktake.
---

# Harness Audit

## Overview

Audit the whole agent harness with one rule above all: **never judge an asset from its text alone — verify every dependency on disk before issuing a verdict.** A plausible-looking SKILL.md whose scripts/ directory is missing fails 100% of the time; a verdict-only review misses exactly these. (Baseline evidence: a prior verdict-only stocktake missed every always-failing skill; the verification pass found revealjs/webapp-testing-class breakage in one run.)

The deliverable is not the verdicts — it is a **fix-instruction document another (cheaper) model can execute without re-deriving the analysis**.

## Phase 1 — Inventory with cost columns

Enumerate assets and measure what actually costs tokens:

```bash
# skills: name, body lines/bytes, frontmatter description length, symlink target
# (description of EVERY skill is injected into EVERY session — sum it)
python3 - <<'EOF'
import os,re
base=os.path.expanduser("~/.claude/skills")
for n in sorted(os.listdir(base)):
    sk=os.path.join(base,n,"SKILL.md")
    if not os.path.exists(sk): continue
    t=open(sk,errors="replace").read()
    m=re.search(r"^description:\s*(.*(?:\n(?:  |\t).*)*)",t,re.M)
    print(n, t.count("\n")+1, len(t.encode()), len(m.group(1)) if m else 0)
EOF
```

Beyond skills, inventory: hooks wired in `settings.json` vs scripts present in `~/.claude/hooks/`; MCP servers registered in `~/.claude.json` vs permission-rule remnants in settings; launchd/cron jobs; symlink-farm integrity (canonical store vs harness mirrors); agents in `~/.claude/agents/`.

Treat usage stats as broken if every asset reads 0 — judge on quality/overlap only, and say so in the report.

## Phase 2 — Evidence verification (the load-bearing step)

For each asset, verify with commands, not reading:

| Claim in the asset | Verification |
|---|---|
| references scripts/, references/, examples/ | `ls` the directory — missing = broken-on-load |
| requires a CLI/binary | `which <bin>` |
| hardcodes a path (`~/tasks/...`, `$HOME/dev/...`) | `ls`/`test -d` |
| routes to another skill/plugin | check it is actually installed |
| claims a hook/command/cron exists | grep settings.json, `ls ~/.claude/commands/`, `launchctl list` |
| env var like `$SKILL_PATH`, `$CODEX_HOME` | confirm this harness sets it |

Unadapted imports are the top defect class: assets lifted from another harness (Codex/chat products), another user's plugin pack, or a dead framework — spot them by wrong agent names, wrong locale defaults, dead sibling links, and decorative metadata for servers that are not installed.

## Phase 3 — Three-axis evaluation via batched subagents

Group assets into **thematic batches (~20)** so one subagent sees a whole family and can catch intra-family overlap/contradiction. Run batches sequentially; **persist each batch's JSON to disk before starting the next** (context may be summarized mid-run).

Each subagent prompt must contain: the axis definitions below, the verification table above, user context (active projects, rules that assets may contradict), and this output contract:

```json
{"name":"...","lines":N,
 "verdict":"Keep|Improve|Update|Retire|Merge into [X]",
 "reason":"self-contained, cites line ranges, states verified evidence",
 "fixes":["executable edit instruction with file + section/line + target size"],
 "priority":"P0|P1|P2"}
```

Axes:
- **Token efficiency**: description ≤ ~400 chars and trigger-only (it is injected every session); body lean (< ~500 lines); long reference material moved to `references/*.md` (progressive disclosure); content the base model already knows (generic language idioms, textbook syntax) is negative value — it costs tokens and can prescribe degraded patterns.
- **Output quality**: concrete commands/code over prose; examples worth imitating; scope matches name and trigger.
- **Stability**: verified-missing dependencies; version-sensitive API/model references; contradictions with the user's global rules; interactive constructs (`read -r`) that hang non-interactive shells.

Retire-bias heuristics: model-baseline restatement → Retire; duplicated trigger space → Merge with a named target and a list of what content to carry over; broken deps → fix if the workflow is real, Retire if fully substitutable. **Never retire load-bearing assets referenced by CLAUDE.md/AGENTS.md** — improve only.

## Phase 4 — Synthesis and handoff

1. Extract cross-cutting patterns (description bloat, dead links, unadapted imports, rule contradictions) — they justify individual verdicts and guide future installs.
2. Write the fix-instruction document with an **execution-principles header**: canonical store location and symlink handling, do-not-edit exceptions (auto-generated or self-updating assets), and a warning that line numbers were valid at audit time — the executor must re-anchor on section headings.
3. **Gate all deletions on explicit user approval** — present the Retire/Merge list as a batch; edits may proceed without approval.
4. Persist: update the results cache. Memory writes are not automatic — record at most one pointer to the audit outcome, and only if it meets the harness's own memory criteria (durable, not derivable from the report file itself). Verify by re-running the Phase 1 scan (expected count delta, no dangling symlinks, frontmatter still valid YAML).

## Common mistakes

| Mistake | Consequence |
|---|---|
| Judging from SKILL.md text without `ls`/`which` | Miss every always-failing asset (the baseline failure) |
| Alphabetical batches | Family overlaps (e.g. three de-AI-ify skills) go undetected |
| Verdicts like "Superseded" without evidence | Executor must re-derive; handoff value lost |
| Fixes without line/section anchors and target sizes | Executor guesses scope, edits drift |
| Deleting before user approval | Irreversible removal of something only the user knew was wanted |
| Trusting usage stats without checking for all-zeros | Retiring on a broken signal |
