---
name: repeat-workflow-packager
description: Find repeated recent workflows and package high-confidence gaps as skills, agents, or automations without duplicating existing ones.
---

# Repeat Workflow Packager

## Goal

Turn repeated, costly, or error-prone work into the smallest useful reusable asset. Prefer evidence over intuition and reuse existing assets before creating new ones.

## Evidence Order

1. Recent Codex sessions and task summaries.
2. Codex Memories and rollout summaries.
3. Chronicle, if enabled, for discovery only. Confirm important details in the source system before relying on them.
4. Existing skills, custom agents, commands, workflows, launch agents, and repo automations.

Useful local locations:

- Codex sessions: `~/.codex/session_index.jsonl`, `~/.codex/sessions/**`
- Codex memories: `~/.codex/memories/MEMORY.md`, `~/.codex/memories/rollout_summaries/**`
- Codex skills: `~/.codex/skills/**/SKILL.md`
- Claude Code skills: `~/.claude/skills/**/SKILL.md`
- Claude Code agents/commands: `~/.claude/agents/**`, `~/.claude/commands/**`
- Local automations: `~/Library/LaunchAgents/**`, repo `.github/workflows/**`

Use `rg` and `rg --files` first. Keep the evidence pass bounded; do not read every session transcript unless exact details are needed.

## Candidate Filter

Package a workflow only when all are true:

- It occurred at least twice, or is clearly likely to recur and costly to repeat.
- It has stable inputs, a repeatable procedure, and a clear output or stopping condition.
- Packaging materially improves speed, quality, consistency, or reliability.
- It is not already adequately covered by an existing skill, agent, command, workflow, or script.

Skip candidates that are one-off, ambiguous, sensitive, weakly evidenced, or already covered.

## Choose The Smallest Form

- **Skill:** reusable workflow, playbook, source map, or review procedure.
- **Custom subagent:** bounded specialist role or repeatable investigation that benefits from delegation.
- **Automation:** scheduled check, recurring report, reminder, or monitor with stable trigger and output.
- **Extend existing:** add a narrow improvement to an existing asset instead of duplicating it.
- **Skip:** insufficient evidence or poor fit.

Prefer a skill when the value is process and context. Prefer a script only when deterministic code is repeatedly rewritten or reliability requires executable checks.

## Required Shortlist

Before creating anything, produce a compact shortlist with:

- repeated workflow
- supporting evidence and dates
- frequency/confidence
- recommended form: skill, subagent, automation, extend existing, or skip
- why it is or is not worth creating

Then create only the high-confidence missing items.

## Creation Rules

1. Keep assets narrow and source-aware. Do not create broad "do everything" skills.
2. Put the canonical skill directory in one location, normally `~/.codex/skills/<skill-name>/` when Codex metadata such as `agents/openai.yaml` is useful.
3. Make the other runtime point at the canonical directory with a symlink, for example `~/.claude/skills/<skill-name> -> ~/.codex/skills/<skill-name>`, to avoid double maintenance.
4. If symlinks are not supported in a future runtime, keep one clearly named canonical source and document any generated copy as derived.
5. For Codex skills, initialize with `~/.codex/skills/.system/skill-creator/scripts/init_skill.py` when creating from scratch.
6. For Claude Code compatibility, prefer the symlinked skill directory; keep frontmatter to `name` and `description` unless the local format clearly requires more.
7. Use `apply_patch` for manual file edits.
8. Do not create README, changelog, or auxiliary docs unless they are directly required by the skill.

## Validation

Run the official Codex validator when possible:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/<skill-name>
```

If it fails because local dependencies such as PyYAML are missing, run a fallback validation:

- Parse `SKILL.md` frontmatter with Ruby or another available YAML parser.
- Confirm `name` matches the folder name.
- Confirm `description` is non-empty and contains trigger context.
- Search for template placeholder leftovers from the initializer.
- Parse `agents/openai.yaml` if present.
- Check the file can be read as ASCII unless there is a clear reason for non-ASCII.

## Final Report

Finish with:

- what was created or extended, with paths
- what was deliberately skipped
- what needs more evidence before packaging
- validation commands and exact blockers if any validation could not run
