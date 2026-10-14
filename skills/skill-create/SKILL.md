---
name: skill-create
description: Create a focused shared SKILL.md from repeated, evidenced local repository practices. Invoke directly as /skill-create; do not use for a one-off project instruction.
disable-model-invocation: true
---

# Skill Create

Use only for an explicit `/skill-create` request. Extract reusable guidance from local repository history without promoting a one-off change, an unverified preference, or generic model knowledge into a shared rule.

Honor requested options: `--commits N` bounds the history, `--output PATH` selects the destination, and `--claude-only` limits installation to Claude. `--shared` is the default. The legacy `--instincts` option needs the separately installed continuous-learning integration; report that dependency if requested rather than inventing it.

## Gather evidence

Inspect a bounded history and the current tree. Adapt the commit count to the repository's age and activity:

```bash
git log --oneline -n 200 --name-only --pretty=format:'%H|%s|%ad' --date=short
git log --oneline -n 200 --name-only | sed '/^$/d;/^[a-f0-9]\{7,\}/d' | sort | uniq -c | sort -rn | head -20
git log --oneline -n 200 | cut -d' ' -f2- | head -50
```

Look for patterns supported by repeated evidence: file co-changes, durable naming or architecture conventions, stable test placement, and recurring workflow sequences. State the evidence and omit low-confidence patterns.

## Write the skill

Create a concise folder named with lowercase letters, digits, and hyphens. Its `SKILL.md` needs frontmatter with `name` and a discriminating `description`, then only the practices that change future decisions.

Use the active skill-creation guidance for frontmatter, progressive disclosure, references, and validation. Keep substantial conditional detail in references only when it is actually needed. Do not add generic checklists, placeholder files, external app integrations, or model routing rules.

## Install once and verify

For the shared local setup, inspect where `$HOME/.agents/skills` entries resolve. When they point into a maintained repository, author the new skill in that repository's `skills/` directory and link it through its installer. Otherwise create it in `$HOME/.agents/skills/<skill-name>`. Then run the installed mirror command:

```bash
bash "$HOME/.agents/sync-skills.sh"
```

This command mirrors the canonical source to supported runtime skill directories. Before relying on it, verify both the command and destination symlinks exist. For another environment or an explicit local-only request, use the user's selected skill root instead; do not create duplicate maintained copies.

Validate the new skill with the local `skill-creator` validator when its Python YAML dependency is installed; otherwise use an available YAML parser and report the missing validator dependency. Also forward-test with a realistic request. Report the evidence, created path, and any practice intentionally excluded for insufficient support.
