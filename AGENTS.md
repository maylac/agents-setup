# Agent Guide

## Purpose

agents-setup is the canonical repo for shared Claude, Codex, skill, command, hook, and home-instruction configuration.

## Structure

- `claude/` and `codex/` mirror harness-specific agents, commands, hooks, and plugin config.
- `skills/` stores shared skills mirrored into local harness homes.
- `home/`, `templates/`, and `manifests/` hold shared instruction and inventory snapshots.
- `scripts/` and `tests/` validate install, backup, and sync behavior.

## Commands

- `scripts/validate.sh` runs the repo validation checks.
- `scripts/audit-sync.sh` checks live-home parity.
- `scripts/backup.sh` refreshes inventory snapshots.

## Guardrails

- Keep unrelated dirty state out of commits; this repo often has local config work in flight.
- Preserve symlink intent when changing shared files.
- Update live home files and repo snapshots together when the task changes runtime behavior.
