#!/usr/bin/env python3
"""Persist compact lifecycle state for Claude Code sessions.

This hook is intentionally advisory: it records local context and asks the
compaction step to preserve decision-critical facts, but never blocks compact.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path.home() / ".claude" / "compact-state"
MAX_TRANSCRIPT_TAIL_BYTES = 200_000


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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception as exc:
        return f"[unavailable: {exc}]"
    return completed.stdout.strip()


def transcript_tail(path: str | None) -> str:
    if not path:
        return ""
    try:
        transcript = Path(path)
        with transcript.open("rb") as fh:
            try:
                fh.seek(-MAX_TRANSCRIPT_TAIL_BYTES, os.SEEK_END)
                fh.readline()
            except OSError:
                fh.seek(0)
            return fh.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return f"[transcript unavailable: {exc}]"


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
    transcript_path = data.get("transcript_path")

    write_text(
        root / "latest-precompact.md",
        "\n".join(
            [
                "# Latest PreCompact Snapshot",
                "",
                f"- captured_at: {timestamp}",
                f"- trigger: {trigger}",
                f"- session_id: {data.get('session_id', 'unknown')}",
                f"- transcript_path: {transcript_path or 'unknown'}",
                "",
                "## Workspace",
                "",
                "```text",
                workspace_snapshot(data).rstrip(),
                "```",
                "",
                "## Transcript Tail",
                "",
                "```jsonl",
                transcript_tail(transcript_path).rstrip(),
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
        if event == "PreCompact":
            handle_precompact(data)
        elif event == "PostCompact":
            handle_postcompact(data)
    except Exception as exc:
        print(f"[compact-recovery] {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
