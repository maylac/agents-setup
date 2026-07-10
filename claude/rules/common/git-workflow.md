---
paths:
  - "**/.github/**"
  - "**/.gitignore"
  - "**/.gitattributes"
description: Git and PR conventions to use when the task involves commits, pushes, or pull requests.
---

# Git Workflow

## Commit Message Format

Use the repository's convention when one exists. Otherwise use:

```text
<type>: <description>

<optional body>
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

Attribution is disabled globally via `~/.claude/settings.json`.

## Pull Request Workflow

When creating PRs:
1. Compare the full branch against its base, not just the latest commit.
2. Summarize user-visible changes and notable implementation choices.
3. Include the exact checks run; say clearly when a relevant check was not run.
4. Push with `-u` only when creating a new branch.
