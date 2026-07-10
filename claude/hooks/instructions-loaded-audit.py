#!/usr/bin/env python3
"""Record instruction load paths and sizes without storing instruction text."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LOG_DIR = Path.home() / ".claude" / "logs" / "instructions-loaded"
RETENTION_DAYS = 30


def read_input() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def candidate_paths(data: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ("file_path", "path", "source", "instruction_file"):
        if key in data:
            values.append(data[key])
    for key in ("files", "paths", "instructions"):
        value = data.get(key)
        if isinstance(value, list):
            values.extend(value)

    paths: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("file_path") or value.get("path")
        if isinstance(value, str) and value:
            paths.append(os.path.expanduser(value))
    return sorted(set(paths))


def prune_logs(now: datetime) -> None:
    if not LOG_DIR.exists():
        return
    cutoff = now - timedelta(days=RETENTION_DAYS)
    for path in LOG_DIR.glob("*.jsonl"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            path.unlink(missing_ok=True)


def main() -> int:
    data = read_input()
    now = datetime.now(timezone.utc)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    prune_logs(now)

    paths = candidate_paths(data)
    record = {
        "captured_at": now.replace(microsecond=0).isoformat(),
        "session_id": data.get("session_id", "unknown"),
        "reason": data.get("trigger") or data.get("matcher") or "unknown",
        "files": [
            {
                "path": path,
                "bytes": Path(path).stat().st_size if Path(path).is_file() else None,
            }
            for path in paths
        ],
    }
    log_file = LOG_DIR / f"{now.date().isoformat()}.jsonl"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
