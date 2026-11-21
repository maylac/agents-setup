#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$repo_root" <<'PY'
import importlib.util
import json
import os
import plistlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

root = Path(sys.argv[1])
script = root / "scripts/harness-heartbeat.py"
heartbeat_plist = plistlib.loads((root / "launchd/com.maylac.harness-heartbeat.plist.template").read_bytes())
require_path = heartbeat_plist["EnvironmentVariables"]["PATH"]
if require_path != "__HOME__/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin":
    raise AssertionError("heartbeat LaunchAgent PATH does not match the portable bridge PATH")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory(prefix="heartbeat-test-") as temporary:
    base = Path(temporary)
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Fixture"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True)
    (repo / "seed.txt").write_text("seed\n")
    subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seed"], check=True)
    subprocess.run(["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    subprocess.run(["git", "-C", str(repo), "switch", "-qc", "heartbeat-work"], check=True)

    agents = base / "LaunchAgents"
    agents.mkdir()
    for label in (
        "local.claude.remote-control",
        "local.claude.remote-control-workspace",
        "local.claude.remote-control-vantik",
        "local.claude.remote-control-ops",
    ):
        (agents / f"{label}.plist").touch()
    poll = base / "last_poll"
    poll.write_text(str(time.time()))
    doctor = base / "doctor.py"
    doctor.write_text(
        "import json, os, sys\n"
        "checks = [] if os.environ.get('FAKE_DOCTOR_EMPTY') else [{'name': 'fixture', 'state': 'present', 'detail': 'private-address-192.0.2.1'}]\n"
        "print(json.dumps({'checks': checks}))\n"
        "raise SystemExit(int(os.environ.get('FAKE_DOCTOR_EXIT', '0')))\n"
    )
    fake_bin = base / "bin"
    fake_bin.mkdir()
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$2\" >> \"$LAUNCHCTL_LOG\"\n"
        "[ \"${MISSING_SERVICE:-}\" = \"$2\" ] && exit 113\n"
        "[ \"${FAIL_SERVICE:-}\" = \"$2\" ] && { echo 'state = waiting'; exit 0; }\n"
        "echo 'state = running'\n"
    )
    launchctl.chmod(0o755)
    state = base / "state"
    env_file = base / "heartbeat.env"
    launchctl_log = base / "launchctl.log"
    env = {"PATH": f"{fake_bin}:{os.environ['PATH']}", "HOME": str(base),
           "LAUNCHCTL_LOG": str(launchctl_log)}

    def invoke(extra=None):
        run_env = dict(env)
        if extra:
            run_env.update(extra)
        return subprocess.run(
            [sys.executable, str(script), "--repo", str(repo), "--doctor", str(doctor),
             "--state-dir", str(state), "--env-file", str(env_file), "--poll-file", str(poll),
             "--launch-agents", str(agents)],
            env=run_env, capture_output=True, text=True, timeout=15,
        )

    good = invoke()
    require(good.returncode == 0, "healthy fixture did not pass")
    status_path = state / "status.json"
    status = json.loads(status_path.read_text())
    require(status["state"] == "ok", "healthy status was not ok")
    require(status_path.stat().st_mode & 0o777 == 0o600, "status mode was not 0600")
    expected_lookups = [
        f"gui/{os.getuid()}/com.maylac.slack-bridge",
        f"gui/{os.getuid()}/local.claude.remote-control",
        f"gui/{os.getuid()}/local.claude.remote-control-workspace",
        f"gui/{os.getuid()}/local.claude.remote-control-vantik",
    ]
    require(launchctl_log.read_text().splitlines() == expected_lookups,
            "launchctl did not receive the four exact required labels")
    require([check["name"] for check in status["checks"] if check["name"].startswith("remote_control_")]
            == ["remote_control_base", "remote_control_workspace", "remote_control_vantik"],
            "required remote control services were not checked by name")
    require(invoke({"MISSING_SERVICE": expected_lookups[1]}).returncode == 1,
            "missing required base service did not fail")
    require(invoke({"FAIL_SERVICE": expected_lookups[1]}).returncode == 1,
            "failed required base service did not fail")
    require(launchctl_log.read_text().splitlines()[-4:] == expected_lookups,
            "optional ops plist replaced a required service lookup")

    behind_file = repo / "main-only.txt"
    behind_file.write_text("main\n")
    subprocess.run(["git", "-C", str(repo), "switch", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", behind_file.name], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "advance local main"], check=True)
    subprocess.run(["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    subprocess.run(["git", "-C", str(repo), "switch", "heartbeat-work"], check=True)
    (repo / "uncommitted.txt").write_text("dirty\n")
    warn = invoke()
    warn_status = json.loads(status_path.read_text())
    scm = next(check for check in warn_status["checks"] if check["name"] == "scm")
    require(warn.returncode == 0 and warn_status["state"] == "ok", "SCM warnings failed health")
    require(scm["state"] == "warn" and scm["dirty_count"] == 1 and scm["behind_main"] == 1,
            "dirty and behind conditions were not warn-only")

    poll.write_text(str(time.time() - 301))
    require(invoke().returncode == 1, "stale poll did not fail")
    poll.unlink()
    require(invoke().returncode == 1, "missing poll did not fail")
    poll.write_text(str(time.time()))
    require(invoke({"FAKE_DOCTOR_EXIT": "1"}).returncode == 1, "failed doctor did not fail")
    require(invoke({"FAKE_DOCTOR_EMPTY": "1"}).returncode == 1,
            "empty doctor checks did not fail")

    env_file.write_text("HEARTBEAT_PING_URL=http://127.0.0.1:9/health\n"
                        "IGNORED=$(touch should-not-exist)\n")
    spec = importlib.util.spec_from_file_location("harness_heartbeat", script)
    heartbeat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(heartbeat)
    parsed = heartbeat.read_env(env_file)
    require(parsed["HEARTBEAT_PING_URL"] == "http://127.0.0.1:9/health",
            "ping URL was not read as data")
    require(not (base / "should-not-exist").exists(), "env data was evaluated as shell")
    requests = []

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return Response()

    heartbeat.urlopen = fake_urlopen
    require(heartbeat.ping(parsed["HEARTBEAT_PING_URL"], False)["state"] == "ok",
            "optional healthy ping did not pass")
    request, timeout = requests[-1]
    require(request.full_url.endswith("/health") and request.get_method() == "POST"
            and request.data == b"ok" and len(request.data) <= 500 and timeout == 5,
            "healthy ping request shape or body was incorrect")
    require(heartbeat.ping(parsed["HEARTBEAT_PING_URL"], True)["state"] == "ok",
            "optional failure ping transport did not pass")
    request, _timeout = requests[-1]
    require(request.full_url.endswith("/health/fail") and request.data == b"fail"
            and len(request.data) <= 500,
            "failure ping did not use /fail and the bounded body")
    with patch.object(heartbeat.shutil, "disk_usage", return_value=SimpleNamespace(free=heartbeat.DISK_FLOOR_BYTES - 1)):
        require(heartbeat.disk_check(repo)["state"] == "fail", "disk below 10 GiB did not fail")

    raw = status_path.read_text()
    require("fixture@example.invalid" not in raw and "should-not-exist" not in raw
            and "private-address-192.0.2.1" not in raw,
            "private fixture data leaked into status")

print("harness heartbeat fixtures passed")
PY
