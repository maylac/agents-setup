#!/usr/bin/env python3
"""Check local harness health and atomically publish a sanitized status file."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


# The configured floor is 10 GiB, using binary bytes (10 * 1024^3).
DISK_FLOOR_BYTES = 10 * 1024 ** 3
POLL_MAX_AGE_SECONDS = 300
BRIDGE_LABEL = "com.maylac.slack-bridge"
REMOTE_CONTROL_LABELS = (
    ("remote_control_base", "local.claude.remote-control"),
    ("remote_control_workspace", "local.claude.remote-control-workspace"),
    ("remote_control_vantik", "local.claude.remote-control-vantik"),
)


def read_env(path):
    values = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key.replace("_", "").isalnum():
                values[key] = value.strip()
    except (OSError, UnicodeError):
        pass
    return values


def run(command, timeout=10):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def doctor_check(doctor):
    result = run([sys.executable, str(doctor)], timeout=120)
    if result is None:
        return {"name": "doctor", "state": "fail"}
    try:
        report = json.loads(result.stdout)
        valid_json = (isinstance(report, dict) and isinstance(report.get("checks"), list)
                      and bool(report["checks"]))
    except (TypeError, ValueError):
        valid_json = False
    return {"name": "doctor", "state": "ok" if result.returncode == 0 and valid_json else "fail"}


def poll_check(path, now):
    try:
        raw = path.read_text(encoding="ascii").strip()
        stamp = float(raw)
        age = now - stamp
        ok = 0 <= age <= POLL_MAX_AGE_SECONDS
        age_seconds = max(0, int(age)) if age >= 0 else None
    except (OSError, ValueError, OverflowError):
        ok, age_seconds = False, None
    return {"name": "poll", "state": "ok" if ok else "fail", "age_seconds": age_seconds}


def service_check(name, target):
    result = run(["launchctl", "print", target])
    state = "fail"
    if result and result.returncode == 0:
        match = re.search(r"\bstate\s*=\s*(\w+)", result.stdout or "")
        if match and match.group(1) == "running":
            state = "ok"
    return {"name": name, "state": state}


def services_check(uid):
    checks = [service_check("bridge", f"gui/{uid}/{BRIDGE_LABEL}")]
    checks.extend(service_check(name, f"gui/{uid}/{label}")
                  for name, label in REMOTE_CONTROL_LABELS)
    return checks


def disk_check(path):
    try:
        free = shutil.disk_usage(path).free
        return {"name": "disk", "state": "ok" if free >= DISK_FLOOR_BYTES else "fail",
                "free_bytes": free, "minimum_bytes": DISK_FLOOR_BYTES}
    except OSError:
        return {"name": "disk", "state": "fail"}


def scm_check(repo):
    branch_result = run(["git", "-C", str(repo), "branch", "--show-current"])
    dirty_result = run(["git", "-C", str(repo), "status", "--porcelain"])
    behind_result = run(["git", "-C", str(repo), "rev-list", "--count", "HEAD..origin/main"])
    valid = all(item and item.returncode == 0 for item in (branch_result, dirty_result))
    branch = (branch_result.stdout or "").strip() if valid else ""
    dirty_count = len((dirty_result.stdout or "").splitlines()) if valid else None
    behind = None
    if behind_result and behind_result.returncode == 0:
        try:
            behind = int(behind_result.stdout.strip())
        except ValueError:
            pass
    warning = not valid or dirty_count != 0 or behind is None or behind > 0
    return {"name": "scm", "state": "warn" if warning else "ok", "branch": branch,
            "dirty_count": dirty_count, "behind_main": behind}


def ping(url, failed):
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return {"name": "ping", "state": "fail"}
    path = parts.path.rstrip("/")
    if failed:
        path += "/fail"
    target = urlunsplit((parts.scheme, parts.netloc, path or "/", parts.query, ""))
    request = Request(target, data=b"ok" if not failed else b"fail", method="POST",
                      headers={"Content-Type": "text/plain; charset=utf-8"})
    try:
        with urlopen(request, timeout=5) as response:
            succeeded = 200 <= response.status < 300
    except (OSError, URLError, ValueError):
        succeeded = False
    return {"name": "ping", "state": "ok" if succeeded else "fail"}


def atomic_status(path, status):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".status-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(status, output, separators=(",", ":"), ensure_ascii=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--doctor", type=Path)
    parser.add_argument("--state-dir", type=Path,
                        default=Path.home() / ".local/state/harness-heartbeat")
    parser.add_argument("--env-file", type=Path,
                        default=Path.home() / ".config/harness-heartbeat/env")
    parser.add_argument("--poll-file", type=Path,
                        default=Path.home() / ".local/state/slack-bridge/last_poll")
    parser.add_argument("--launch-agents", type=Path,
                        default=Path.home() / "Library/LaunchAgents")
    args = parser.parse_args(argv)

    doctor = args.doctor or args.repo / "slack-bridge/doctor.py"
    now = time.time()
    checks = [doctor_check(doctor), poll_check(args.poll_file, now)]
    checks.extend(services_check(os.getuid()))
    checks.extend((disk_check(args.repo), scm_check(args.repo)))
    failed = any(item["state"] == "fail" for item in checks)
    checks.append({"name": "result", "state": "fail" if failed else "ok"})
    status = {"timestamp": int(now), "state": "fail" if failed else "ok", "checks": checks}
    atomic_status(args.state_dir / "status.json", status)
    ping_check = ping(read_env(args.env_file).get("HEARTBEAT_PING_URL", ""), failed)
    if ping_check:
        checks.append(ping_check)
        atomic_status(args.state_dir / "status.json", status)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
