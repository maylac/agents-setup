# Rules

## Structure

Rules are organized into a **common** layer plus a small set of **language-specific** directories:

```
claude/rules/
├── common/          # Language-agnostic principles (always installed)
│   ├── coding-style.md
│   ├── git-workflow.md
│   ├── testing.md
│   ├── performance.md
│   ├── patterns.md
│   ├── hooks.md
│   ├── agents.md
│   └── security.md
├── typescript/      # TypeScript/JavaScript specific
├── python/          # Python specific
├── swift/           # Swift specific
└── kotlin/          # Kotlin/Android/KMP specific
```

- **common/** contains universal principles — no language-specific code examples.
- **Language directories** are kept thin (roughly 20-50 lines per file): project-specific judgment calls plus a `See skill: <name>` pointer for detailed idioms and code examples. Only languages actually in use in this workspace are kept here — see [../scripts/README.md](../scripts/README.md) or run `scripts/install.sh --check` for current coverage. Other languages can be added back the same way if a project needs them (see "Adding a New Language" below).

## Installation

This repo is the canonical source. `~/.claude/rules/common` and each `~/.claude/rules/<language>` are symlinks into this repo, kept in sync by `scripts/install.sh`.

```bash
# Dry-run: show what would change
scripts/install.sh --instructions-only

# Apply: (re)create the canonical symlinks
scripts/install.sh --apply-instructions
```

Do not `cp -r` these directories — the live install must stay symlinked so edits here take effect immediately and `scripts/backup.sh`/`scripts/install.sh --check` can detect drift.

## Rules vs Skills

- **Rules** define project-specific judgment calls and conventions that apply broadly, scoped to files matching a `paths:` glob.
- **Skills** (`~/.agents/skills/`) provide deep, actionable reference material and code examples for specific tasks (e.g., `python-patterns`, `kotlin-testing`).

Language-specific rule files reference relevant skills via a `See skill: <name>` line. Rules tell you *what* project-specific choice to make; skills tell you *how* to implement it in depth.

## Adding a New Language

To add a language directory back:

1. Create `claude/rules/<language>/` in this repo with the standard file set:
   - `coding-style.md`, `testing.md`, `patterns.md`, `hooks.md`, `security.md`
2. Keep each file thin — project-specific judgment calls only, not a tutorial. Start with:
   ```
   > This file extends [common/xxx.md](../common/xxx.md) with <Language> specific content.
   ```
3. End with a `## Reference` section pointing to the relevant skill(s), if any exist.
4. Add the directory to the symlink lists in `scripts/install.sh` (`show_instruction_dry_run` and `apply_instruction_symlinks`).
5. Run `scripts/install.sh --apply-instructions` to create the live symlink.

## Rule Priority

When language-specific rules and common rules conflict, **language-specific rules take precedence** (specific overrides general) — see `rules/common/README.md` note in `claude/CLAUDE.md`. This follows the standard layered configuration pattern (similar to CSS specificity or `.gitignore` precedence).
