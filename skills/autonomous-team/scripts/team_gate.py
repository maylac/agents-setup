#!/usr/bin/env python3
"""Session-scoped evidence gate for the autonomous-team skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MAX_STOP_BLOCKS = 2
FILTER_KEY_RE = re.compile(r"^filter\..+\.(clean|process|required)$", re.I)
GIT_CONFIG = [
    "core.fsmonitor=false",
    "core.untrackedCache=false",
    "diff.external=",
    f"core.hooksPath={os.devnull}",
]


class GateError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(root: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    command = ["git", "-C", str(root), "--no-pager", "--literal-pathspecs"]
    configs = list(GIT_CONFIG)
    env = os.environ.copy()
    for key in list(env):
        if key in {"GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"} or re.fullmatch(r"GIT_CONFIG_(?:KEY|VALUE)_\d+", key):
            env.pop(key, None)
    env["GIT_PAGER"] = "cat"
    env.pop("GIT_EXTERNAL_DIFF", None)
    # Config lookup returns key names only. Never read or display filter values.
    if not (args and args[0] == "config" and "--get-regexp" in args):
        query = subprocess.run(
            command + [flag for item in configs for flag in ("-c", item)]
            + ["config", "--name-only", "--get-regexp", r"^filter\..*\.(clean|process|required)$"],
            text=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if query.returncode not in (0, 1):
            raise subprocess.CalledProcessError(query.returncode, query.args, query.stdout, query.stderr)
        filter_overrides = []
        for name in query.stdout.splitlines():
            if FILTER_KEY_RE.fullmatch(name):
                value = "false" if name.lower().endswith(".required") else ""
                filter_overrides.append((name, value))
        env["GIT_CONFIG_COUNT"] = str(len(filter_overrides))
        for index, (name, value) in enumerate(filter_overrides):
            env[f"GIT_CONFIG_KEY_{index}"] = name
            env[f"GIT_CONFIG_VALUE_{index}"] = value
    for item in configs:
        command.extend(("-c", item))
    for arg in args:
        if arg == "diff":
            command.extend((arg, "--no-ext-diff", "--no-textconv"))
        else:
            command.append(arg)
    return subprocess.run(command, check=True, text=text, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git(root: Path, *args: str) -> str:
    result = run_git(root, *args, text=True)
    return result.stdout.strip()


def repo_root(cwd: str | Path) -> Path:
    path = Path(cwd).expanduser().resolve()
    try:
        return Path(git(path, "rev-parse", "--show-toplevel")).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise GateError(f"not inside a Git checkout: {path}") from exc


def state_path(root: Path, session: str) -> Path:
    if not SESSION_RE.fullmatch(session):
        raise GateError("session ID must be 1-80 safe letters, digits, dot, underscore, or dash")
    common = Path(git(root, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    directory = common / "team-runs" / "autonomous-team"
    checkout_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    return directory / f"{session}-{checkout_id}.json"


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".team-gate-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"session state is unreadable: {path}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise GateError("session state has an unsupported or invalid format")
    return value


def changed_paths(root: Path, base_sha: str) -> list[str]:
    tracked = run_git(root, "diff", "--no-renames", "--ignore-submodules=dirty",
                       "--name-only", "-z", base_sha).stdout
    untracked = run_git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    values = {item.decode("utf-8", "surrogateescape") for item in tracked.split(b"\0") if item}
    values.update(item.decode("utf-8", "surrogateescape") for item in untracked.split(b"\0") if item)
    return sorted(values)


def status_map(root: Path) -> dict[str, str]:
    raw = run_git(root, "status", "--ignore-submodules=dirty", "--porcelain=v1", "-z",
                   "--untracked-files=all").stdout
    records = raw.split(b"\0")
    result: dict[str, str] = {}
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2].decode("ascii", "replace")
        name = record[3:].decode("utf-8", "surrogateescape")
        result[name] = status
        if "R" in status or "C" in status:
            if index < len(records) and records[index]:
                result[records[index].decode("utf-8", "surrogateescape")] = status
                index += 1
    return result


def path_fingerprint(root: Path, name: str, status: str) -> str:
    path = root / name
    digest = hashlib.sha256()
    digest.update(status.encode("ascii", "replace"))
    try:
        if path.is_symlink():
            content = b"link\0" + os.readlink(path).encode("utf-8", "surrogateescape")
        elif path.is_file():
            content = f"file:{stat.S_IMODE(path.stat().st_mode)}\0".encode() + path.read_bytes()
        elif path.is_dir():
            content = b"directory"
        else:
            content = b"missing"
    except OSError as exc:
        raise GateError(f"cannot fingerprint {name}: {exc}") from exc
    digest.update(content)
    return digest.hexdigest()


def is_owned(changed: str, owned: list[str]) -> bool:
    return any(changed == path.rstrip("/") or (path.endswith("/") and changed.startswith(path))
               for path in owned)


def scope_violations(root: Path, state: dict[str, Any]) -> list[str]:
    owned = state.get("owned_paths")
    if not isinstance(owned, list) or not owned:
        return ["contract has no owned paths"]
    baseline = state.get("baseline_out_of_scope", {})
    violations = []
    current_paths = changed_paths(root, str(state.get("base_sha", "")))
    statuses = status_map(root)
    for changed in current_paths:
        if is_owned(changed, owned):
            continue
        previous = baseline.get(changed) if isinstance(baseline, dict) else None
        if previous and path_fingerprint(root, changed, statuses.get(changed, "")) == previous:
            continue
        violations.append(changed)
    if isinstance(baseline, dict):
        for name, previous in baseline.items():
            if name not in current_paths and path_fingerprint(root, name, statuses.get(name, "")) != previous:
                violations.append(name)
    return sorted(set(violations))


def snapshot(root: Path, state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    base_sha = str(state["base_sha"])
    diff = run_git(root, "diff", "--no-renames", "--ignore-submodules=dirty",
                   "--binary", base_sha).stdout
    digest.update(b"tracked-diff\0")
    digest.update(diff)
    for name in changed_paths(root, base_sha):
        path = root / name
        digest.update(b"untracked-or-path\0" + name.encode("utf-8", "surrogateescape") + b"\0")
        try:
            if path.is_symlink():
                content = os.readlink(path).encode("utf-8", "surrogateescape")
            elif path.is_file():
                content = f"{stat.S_IMODE(path.stat().st_mode)}\0".encode() + path.read_bytes()
            elif path.is_dir():
                content = b"directory"
            else:
                content = b"missing"
        except OSError as exc:
            raise GateError(f"cannot hash changed path {name}: {exc}") from exc
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def load_for(root: Path, session: str) -> tuple[Path, dict[str, Any]]:
    path = state_path(root, session)
    state = read_state(path)
    if Path(state.get("cwd", "")).resolve() != root:
        raise GateError("session belongs to a different checkout path")
    return path, state


def require_fresh_checks(root: Path, state: dict[str, Any]) -> str:
    violations = scope_violations(root, state)
    if violations:
        raise GateError("changes outside owned paths: " + ", ".join(violations[:8]))
    current = snapshot(root, state)
    checks = state.get("checks")
    if not isinstance(checks, dict) or checks.get("snapshot") != current:
        raise GateError("acceptance checks are missing or stale; run check again")
    if not checks.get("passed"):
        raise GateError("one or more acceptance checks failed")
    log_path = state_path(root, str(state.get("session", ""))).with_suffix(".checks.log")
    try:
        log_hash = hashlib.sha256(log_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise GateError("acceptance command log is missing or unreadable") from exc
    if log_hash != checks.get("log_sha256"):
        raise GateError("acceptance command log changed after it was recorded")
    return current


def require_fresh_evidence(root: Path, state: dict[str, Any]) -> None:
    current = require_fresh_checks(root, state)
    review = state.get("review")
    if not isinstance(review, dict) or review.get("snapshot") != current:
        raise GateError("review is missing or stale; review the current integrated diff")
    if review.get("outcome") != "pass":
        raise GateError("review has findings and cannot authorize ready")
    evidence = Path(str(review.get("evidence", "")))
    try:
        evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    except OSError as exc:
        raise GateError("review evidence is missing or unreadable") from exc
    if evidence_hash != review.get("evidence_sha256"):
        raise GateError("review evidence changed after it was recorded")


def command_init(args: argparse.Namespace) -> int:
    root = repo_root(args.cwd)
    head = git(root, "rev-parse", "HEAD")
    if head != args.base_sha:
        raise GateError(f"base SHA mismatch: checkout HEAD is {head}, contract says {args.base_sha}")
    owned: list[str] = []
    for raw in args.owned_path:
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts or not raw.strip("/"):
            raise GateError(f"owned path must be a repo-relative path: {raw}")
        is_directory = raw.endswith("/")
        normalized = candidate.as_posix().rstrip("/")
        if normalized in ("", ".", ".git") or normalized.startswith(".git/"):
            raise GateError(f"invalid owned path: {raw}")
        owned.append(normalized + ("/" if is_directory else ""))
    if not owned or not args.check:
        raise GateError("init requires at least one --owned-path and one --check")
    path = state_path(root, args.session)
    if path.exists():
        raise GateError(f"session already exists: {args.session}; use a new session ID")
    initial = changed_paths(root, head)
    dirty_owned = [name for name in initial if is_owned(name, owned)]
    if dirty_owned:
        raise GateError("checkout already has dirty owned paths; use a clean task worktree: "
                        + ", ".join(dirty_owned[:8]))
    statuses = status_map(root)
    baseline = {name: path_fingerprint(root, name, statuses.get(name, "")) for name in initial}
    state = {
        "version": 1,
        "session": args.session,
        "cwd": str(root),
        "base_sha": head,
        "owned_paths": sorted(set(owned)),
        "baseline_out_of_scope": baseline,
        "checks_contract": args.check,
        "created_at": now(),
        "status": "active",
        "stop_blocks": 0,
    }
    atomic_json(path, state)
    print(f"initialized {args.session} at {head}; state stored outside the worktree")
    return 0


def command_check(args: argparse.Namespace) -> int:
    root = repo_root(args.cwd)
    path, state = load_for(root, args.session)
    violations = scope_violations(root, state)
    if violations:
        raise GateError("changes outside owned paths: " + ", ".join(violations[:8]))
    outcomes = []
    for command in state["checks_contract"]:
        completed = subprocess.run(command, cwd=root, shell=True, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outcomes.append({
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4096:],
            "stderr": completed.stderr[-4096:],
        })
        print(f"{'PASS' if completed.returncode == 0 else 'FAIL'}: {command}")
    after_violations = scope_violations(root, state)
    current = snapshot(root, state)
    state["checks"] = {
        "completed_at": now(),
        "snapshot": current,
        "passed": all(item["exit_code"] == 0 for item in outcomes) and not after_violations,
        "results": [{key: value for key, value in item.items() if key not in {"stdout", "stderr"}}
                    for item in outcomes],
    }
    state.pop("review", None)
    state["status"] = "active"
    if state["checks"]["passed"]:
        state["stop_blocks"] = 0
    log_path = path.with_suffix(".checks.log")
    log_lines = []
    for index, item in enumerate(outcomes, 1):
        log_lines.append(f"[{index}] {item['command']} (exit={item['exit_code']})")
        if item["stdout"]:
            log_lines.append("stdout:\n" + item["stdout"])
        if item["stderr"]:
            log_lines.append("stderr:\n" + item["stderr"])
    log_content = ("\n\n".join(log_lines) + "\n").encode("utf-8")
    log_path.write_bytes(log_content)
    state["checks"]["log_sha256"] = hashlib.sha256(log_content).hexdigest()
    atomic_json(path, state)
    for item in outcomes:
        if item["exit_code"] != 0:
            if item["stdout"]:
                print("stdout (last 4096 chars):\n" + item["stdout"])
            if item["stderr"]:
                print("stderr (last 4096 chars):\n" + item["stderr"])
    print(f"check log: {log_path}")
    if after_violations:
        raise GateError("checks created changes outside owned paths: " + ", ".join(after_violations[:8]))
    if not state["checks"]["passed"]:
        raise GateError("acceptance checks failed")
    print(f"recorded checks for workspace {current}")
    return 0


def command_review(args: argparse.Namespace) -> int:
    root = repo_root(args.cwd)
    path, state = load_for(root, args.session)
    current = require_fresh_checks(root, state)
    if args.snapshot != current:
        raise GateError(f"review snapshot mismatch: current snapshot is {current}")
    evidence = Path(args.evidence).expanduser().resolve()
    if evidence == root or root in evidence.parents:
        raise GateError("review evidence must be outside the checkout")
    try:
        content = evidence.read_bytes()
    except OSError as exc:
        raise GateError(f"cannot read review evidence: {evidence}") from exc
    if not content.strip():
        raise GateError("review evidence is empty")
    required_line = f"Snapshot: {current}"
    if required_line not in content.decode("utf-8", "replace").splitlines():
        raise GateError(f"review evidence must include the exact line: {required_line}")
    state["review"] = {
        "completed_at": now(),
        "outcome": args.outcome,
        "snapshot": current,
        "evidence": str(evidence),
        "evidence_sha256": hashlib.sha256(content).hexdigest(),
    }
    state["status"] = "active"
    if args.outcome == "pass":
        state["stop_blocks"] = 0
    atomic_json(path, state)
    print(f"recorded review={args.outcome} for workspace {current}")
    return 0


def command_snapshot(args: argparse.Namespace) -> int:
    root = repo_root(args.cwd)
    _, state = load_for(root, args.session)
    current = require_fresh_checks(root, state)
    print(f"Snapshot: {current}")
    return 0


def command_finish(args: argparse.Namespace) -> int:
    root = repo_root(args.cwd)
    path, state = load_for(root, args.session)
    if args.outcome == "ready":
        require_fresh_evidence(root, state)
    elif not args.reason.strip():
        raise GateError(f"finish outcome {args.outcome} requires --reason")
    state["status"] = args.outcome
    state["reason"] = args.reason.strip()
    state["finished_at"] = now()
    atomic_json(path, state)
    print(f"recorded outcome: {args.outcome}" + (f" — {state['reason']}" if state["reason"] else ""))
    return 0


HIGH_RISK_PATTERNS = [
    (re.compile(r"\bgit\s+push\b[^\n;&|]*\s(--force(?:-with-lease)?|-f)(?:\s|$)", re.I), "force push"),
    (re.compile(r"\bgit\s+push\b[^\n;&|]*\s(?:origin|upstream)\s+(?:main|master)(?:\s|$)", re.I), "push to the default branch"),
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.I), "destructive history reset"),
    (re.compile(r"\bgit\s+(?:clean\s+-[a-z]*f|restore\s+|checkout\s+--\s)", re.I), "discarding local files"),
    (re.compile(r"\bgit\s+rebase\b", re.I), "history rewrite"),
    (re.compile(r"\bgit\s+tag\b[^\n;&|]*\s-f(?:\s|$)", re.I), "tag rewrite"),
    (re.compile(r"\bgh\s+pr\s+merge\b|\bgh\s+release\s+(?:create|edit)\b", re.I), "PR merge or release"),
    (re.compile(r"\b(?:npm|pnpm|yarn)\s+publish\b|\btwine\s+upload\b|\bpython\s+-m\s+build\b[^\n]*\bpublish\b", re.I), "package publish"),
    (re.compile(r"\b(?:vercel\s+.*--prod|wrangler\s+deploy|terraform\s+apply|kubectl\s+apply)\b", re.I), "deployment or infrastructure change"),
]


def command_is_risky(command: str, cwd: str | None) -> str | None:
    for pattern, label in HIGH_RISK_PATTERNS:
        if pattern.search(command):
            return label
    if re.search(r"\bgit\s+merge\b", command, re.I):
        try:
            branch = git(repo_root(cwd or Path.cwd()), "branch", "--show-current")
            if branch in {"main", "master"}:
                return "merge into the default branch"
        except GateError:
            pass
    return None


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False))


def hook_pre(_args: argparse.Namespace | None = None) -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    if payload.get("tool_name") != "Bash":
        return 0
    command = str(tool_input.get("command", ""))
    reason = command_is_risky(command, payload.get("cwd"))
    if reason:
        emit({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"Autonomous Team approval gate: {reason}. Review the exact command and obtain required approval.",
        }})
    return 0


def hook_stop(_args: argparse.Namespace | None = None) -> int:
    try:
        payload = json.load(sys.stdin)
        session = str(payload.get("session_id", ""))
        if not session or not SESSION_RE.fullmatch(session):
            return 0
        try:
            root = repo_root(payload.get("cwd") or Path.cwd())
        except GateError:
            return 0
        path = state_path(root, session)
        if not path.exists():
            return 0
        try:
            state = read_state(path)
        except GateError as exc:
            count_path = path.with_suffix(".invalid-count")
            try:
                count = int(count_path.read_text(encoding="ascii")) if count_path.exists() else 0
            except (OSError, ValueError):
                count = 0
            count += 1
            count_path.write_text(str(count), encoding="ascii")
            if count == 1:
                emit({"decision": "block", "reason": f"Autonomous Team state is invalid: {exc}. Record a blocked outcome or repair the session state."})
            else:
                emit({"continue": True, "systemMessage": "AUTONOMOUS TEAM UNVERIFIED: session state is invalid; report the task as unverified."})
            return 0
        if Path(state.get("cwd", "")).resolve() != root:
            return 0
        if state.get("status") in {"blocked", "approval-required"}:
            return 0
        try:
            if state.get("status") != "ready":
                raise GateError("no terminal outcome has been recorded")
            require_fresh_evidence(root, state)
            return 0
        except GateError as exc:
            blocks = int(state.get("stop_blocks", 0))
            if blocks < MAX_STOP_BLOCKS:
                state["stop_blocks"] = blocks + 1
                atomic_json(path, state)
                emit({"decision": "block", "reason": f"Autonomous Team gate: {exc}. Complete the missing evidence or record blocked/approval-required."})
            else:
                emit({"continue": True, "systemMessage": f"AUTONOMOUS TEAM UNVERIFIED: {exc}. Do not report success; the stop gate reached its two-intervention limit."})
            return 0
    except Exception as exc:  # Hook failures must be visible and must not claim completion.
        emit({"continue": True, "systemMessage": f"AUTONOMOUS TEAM UNVERIFIED: stop hook diagnostic failure ({type(exc).__name__}); do not report success."})
        return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--session", required=True)
    init.add_argument("--cwd", required=True)
    init.add_argument("--base-sha", required=True)
    init.add_argument("--owned-path", action="append", default=[])
    init.add_argument("--check", action="append", default=[])
    init.set_defaults(func=command_init)
    for name, func in (("check", command_check),):
        item = sub.add_parser(name)
        item.add_argument("--session", required=True)
        item.add_argument("--cwd", required=True)
        item.set_defaults(func=func)
    review = sub.add_parser("review")
    review.add_argument("--session", required=True)
    review.add_argument("--cwd", required=True)
    review.add_argument("--outcome", choices=("pass", "findings"), required=True)
    review.add_argument("--evidence", required=True)
    review.add_argument("--snapshot", required=True)
    review.set_defaults(func=command_review)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--session", required=True)
    snap.add_argument("--cwd", required=True)
    snap.set_defaults(func=command_snapshot)
    finish = sub.add_parser("finish")
    finish.add_argument("--session", required=True)
    finish.add_argument("--cwd", required=True)
    finish.add_argument("--outcome", choices=("ready", "blocked", "approval-required"), required=True)
    finish.add_argument("--reason", default="")
    finish.set_defaults(func=command_finish)
    for name in ("hook-pre", "hook-stop"):
        item = sub.add_parser(name)
        item.set_defaults(func=hook_pre if name == "hook-pre" else hook_stop)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (GateError, subprocess.CalledProcessError) as exc:
        message = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            message = exc.stderr.decode(errors="replace").strip() if isinstance(exc.stderr, bytes) else exc.stderr.strip()
        print(f"team_gate: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
