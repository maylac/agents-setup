#!/usr/bin/env python3
"""Report removable myLife worktrees without deleting anything."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def worktrees(repo: Path) -> list[dict[str, str]]:
    result = git(repo, "worktree", "list", "--porcelain")
    result.check_returncode()
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return records


def worktree_age(path: Path) -> int | None:
    match = re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name)
    if not match:
        return None
    return (date.today() - datetime.strptime(path.name, "%Y-%m-%d").date()).days


def classify(repo: Path, record: dict[str, str]) -> dict[str, str | int | bool | None]:
    path = Path(record["worktree"])
    head = record.get("HEAD", "unknown")
    branch = record.get("branch", "detached").removeprefix("refs/heads/")
    dirty = len(git(path, "status", "--porcelain=v1").stdout.splitlines())
    age = worktree_age(path)
    merged = git(repo, "merge-base", "--is-ancestor", head, "main").returncode == 0
    upstream_result = git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else ""
    ahead = int(git(path, "rev-list", "--count", f"{upstream}..HEAD").stdout or "0") if upstream else None

    if path == repo:
        status = "KEEP_PRIMARY"
    elif dirty:
        status = "KEEP_DIRTY"
    elif age is None or age <= 3:
        status = "KEEP_RECENT"
    elif merged and upstream and ahead == 0:
        status = "CANDIDATE_REVIEW"
    else:
        status = "KEEP_UNVERIFIED"

    return {
        "path": str(path),
        "branch": branch,
        "dirty": dirty,
        "age": age,
        "merged": merged,
        "upstream": upstream or "none",
        "ahead": ahead,
        "status": status,
    }


def render(repo: Path) -> str:
    rows = [classify(repo, record) for record in worktrees(repo)]
    lines = [
        "# myLife Worktree Retention Report",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "This report is advisory only. It never removes worktrees.",
        "",
        "| Status | Age | Dirty | Merged | Ahead | Branch | Path |",
        "|---|---:|---:|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {status} | {age} | {dirty} | {merged} | {ahead} | `{branch}` | `{path}` |".format(
                **{key: ("-" if value is None else value) for key, value in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "Removal gate: only `CANDIDATE_REVIEW` entries may proceed to explicit user approval, followed by `git worktree remove`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.home() / "workspace" / "myLife")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = render(args.repo.resolve())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + ".tmp")
        temp.write_text(report, encoding="utf-8")
        temp.replace(args.output)
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
