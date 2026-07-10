# Agents Setup

Public-safe backup and restore scaffold for global agent assets used across
Claude Code, Codex, and related local agent tooling.

This repository is intentionally not a full copy of `~/.claude` or `~/.codex`.
Those directories contain sessions, caches, databases, and credentials. The
repo keeps reusable assets and restore instructions:

- public-safe global skills from `~/.agents/skills`
- home-level `AGENTS.md` / `CLAUDE.md` instruction snapshots
- Claude/Codex instruction files, RTK guidance, rules, agents, hooks, and output styles that pass redaction checks
- plugin inventory and restore notes
- public templates for settings that should not be copied verbatim
- an AI config sync manifest and audit for Claude/Codex paired behavior
- validation scripts that block common secret and local-path leaks

## Layout

```text
skills/              Public-safe global skills
home/                Home-level AGENTS.md and CLAUDE.md symlink snapshot
claude/              Claude Code instructions, rules, agents, hooks, output styles, and plugin inventory
codex/               Codex instructions, agents, hooks, and plugin inventory
docs/                Restore and public-safety notes
manifests/           Generated inventory and exclusion notes
scripts/             Backup, restore, and validation helpers
templates/           Public-safe config templates
```

## Refresh

```sh
scripts/backup.sh
scripts/validate.sh
scripts/audit-sync.sh
```

Refresh only the canonical instruction snapshot:

```sh
scripts/backup.sh --instructions-only
```

`backup.sh` copies only public-safe candidates and rewrites local home paths to
`$HOME`. It excludes known runtime state, caches, sessions, databases, and
assets that require manual review before public release.

## Restore

Run a dry-run first. This reports instruction diffs and skill symlink changes:

```sh
scripts/install.sh
```

Make this repo the canonical source for instruction files and rules:

```sh
scripts/install.sh --apply-instructions --instructions-only
```

Apply symlinks for skills only:

```sh
scripts/install.sh --apply
```

Hooks, plugins, and main settings are documented in `docs/restore.md` because
they can include machine-specific trust hashes, application paths, or auth
state.
