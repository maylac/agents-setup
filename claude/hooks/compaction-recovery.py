#!/usr/bin/env python3
"""Persist compact lifecycle state for Claude Code sessions.

This hook is intentionally advisory: it records local context and asks the
compaction step to preserve decision-critical facts, but never blocks compact.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path.home() / ".claude" / "compact-state"
RETENTION_DAYS = 30
MAX_SESSION_DIRS = 10


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str | None) -> str:
    value = value or "unknown"
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return value[:120] or "unknown"


def run(cmd: list[str], cwd: str | None) -> str:
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd if cwd and os.path.isdir(cwd) else None,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception as exc:
        return f"[unavailable: {exc}]"
    return completed.stdout.strip()


def read_input() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def event_dir(data: dict[str, Any]) -> Path:
    return BASE_DIR / safe_name(data.get("session_id"))


def prune_state() -> None:
    """Keep compact metadata bounded without retaining conversation text."""
    if not BASE_DIR.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    session_dirs = sorted(
        (path for path in BASE_DIR.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for index, path in enumerate(session_dirs):
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if index >= MAX_SESSION_DIRS or modified < cutoff:
            shutil.rmtree(path, ignore_errors=True)


def workspace_snapshot(data: dict[str, Any]) -> str:
    cwd = data.get("cwd") or data.get("workspace", {}).get("current_dir")
    parts = [
        f"cwd: {cwd or 'unknown'}",
        "",
        "git branch:",
        run(["git", "branch", "--show-current"], cwd),
        "",
        "git status --short:",
        run(["git", "status", "--short"], cwd),
        "",
        "git diff --stat:",
        run(["git", "diff", "--stat"], cwd),
    ]
    return "\n".join(parts).strip() + "\n"


def handle_precompact(data: dict[str, Any]) -> None:
    root = event_dir(data)
    timestamp = now_iso()
    trigger = data.get("trigger") or "unknown"

    write_text(
        root / "latest-precompact.md",
        "\n".join(
            [
                "# Latest PreCompact Snapshot",
                "",
                f"- captured_at: {timestamp}",
                f"- trigger: {trigger}",
                f"- session_id: {data.get('session_id', 'unknown')}",
                "",
                "## Workspace",
                "",
                "```text",
                workspace_snapshot(data).rstrip(),
                "```",
                "",
            ]
        ),
    )

    context = (
        "Compact preservation reminder: preserve the current objective, decisions "
        "and reasons, rejected approaches, files touched/read, verification already "
        "run, unresolved issues, and exact next actions. A local precompact snapshot "
        f"was saved at {root / 'latest-precompact.md'}."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreCompact",
                    "additionalContext": context,
                }
            }
        )
    )


def handle_postcompact(data: dict[str, Any]) -> None:
    root = event_dir(data)
    timestamp = now_iso()
    summary = data.get("compact_summary") or ""
    trigger = data.get("trigger") or "unknown"

    write_text(
        root / "latest-postcompact.md",
        "\n".join(
            [
                "# Latest PostCompact Summary",
                "",
                f"- captured_at: {timestamp}",
                f"- trigger: {trigger}",
                f"- session_id: {data.get('session_id', 'unknown')}",
                "",
                "## Compact Summary",
                "",
                summary.rstrip() or "none provided",
                "",
            ]
        ),
    )


def main() -> int:
    data = read_input()
    event = data.get("hook_event_name")
    try:
        prune_state()
        if event == "PreCompact":
            handle_precompact(data)
        elif event == "PostCompact":
            handle_postcompact(data)
    except Exception as exc:
        print(f"[compact-recovery] {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
