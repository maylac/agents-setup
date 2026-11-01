#!/usr/bin/env python3
"""Read-only preflight for the local Slack/GitHub bridge."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def check(name, state, detail):
    return {"name": name, "state": state, "detail": detail}


def read_env(path):
    """Parse simple KEY=value entries; never evaluate shell syntax."""
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    except OSError:
        return {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key.replace("_", "").isalnum():
            values[key] = value
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".config/slack-bridge/env")
    parser.add_argument("--check-github", action="store_true", help="run read-only gh repo view")
    args = parser.parse_args(argv)

    checks = []
    env = read_env(args.env_file)
    checks.append(check("env_file", "present" if env is not None else "missing",
                        "read as data; shell expressions are not evaluated"))
    if env is None:
        env = {}
    transport = env.get("BRIDGE_TRANSPORT", "slack")
    required = ["BRIDGE_ALLOWED_SENDERS", "BRIDGE_ALLOWED_REPOS"]
    required += (["BRIDGE_GITHUB_REPO"] if transport == "github" else
                 ["SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"] if transport == "slack" else [])
    for key in required:
        value = env.get(key, "")
        checks.append(check("config:" + key, "present" if value else "missing",
                            "value not displayed"))

    repo_values = [p.strip() for p in env.get("BRIDGE_ALLOWED_REPOS", "").split(",") if p.strip()]
    if not repo_values:
        checks.append(check("allowed_repositories", "missing", "no repository paths configured"))
    else:
        for raw in repo_values:
            # Match bridge's path handling without expanding shell variables.
            path = Path(os.path.realpath(os.path.expanduser(raw)))
            checks.append(check("allowed_repository", "present" if path.is_dir() else "missing",
                                str(path)))

    for name, configured in (("claude", "claude"), ("codex", env.get("BRIDGE_CODEX_BIN", "codex")),
                             ("agy", "agy"), ("grok", env.get("BRIDGE_GROK_BIN", "grok")),
                             ("cursor", env.get("BRIDGE_CURSOR_BIN", "cursor-agent"))):
        found = shutil.which(configured)
        gated_off = (name == "grok" and env.get("BRIDGE_GROK_ENABLED") != "1") or (
            name == "cursor" and env.get("BRIDGE_CURSOR_ENABLED") != "1")
        state = "disabled" if gated_off else "present" if found else "missing"
        checks.append(check("cli:" + name, state, found or "executable not found on PATH"))
        if name == "cursor" and found and not gated_off:
            try:
                result = subprocess.run([found, "--help"], capture_output=True, text=True, timeout=10)
                help_text = result.stdout + "\n" + result.stderr
                identity = (result.returncode == 0 and re.search(r"(?i)\bcursor\s+(?:cli|agent)\b", help_text)
                            and "-p" in help_text and "--output-format" in help_text
                            and re.search(r"(?i)\btext\b", help_text)
                            and "--mode" in help_text and re.search(r"\bask\b", help_text))
                checks.append(check("cursor_identity", "present" if identity else "unknown",
                                    "help identifies Cursor print/text and --mode ask options" if identity else
                                    "configured executable identity/options not confirmed"))
            except (OSError, subprocess.TimeoutExpired):
                checks.append(check("cursor_identity", "unknown", "help check unavailable"))

    if sys_platform_is_macos():
        label = "gui/%d/com.maylac.slack-bridge" % os.getuid()
        try:
            result = subprocess.run(["launchctl", "print", label], capture_output=True, text=True, timeout=5)
            active = result.returncode == 0
            checks.append(check("launchd", "present" if active else "missing",
                                "service status queried; output omitted"))
        except (OSError, subprocess.TimeoutExpired):
            checks.append(check("launchd", "unknown", "launchctl status unavailable"))
    else:
        checks.append(check("launchd", "unknown", "status check is macOS-only"))

    if args.check_github:
        gh_repo = env.get("BRIDGE_GITHUB_REPO", "")
        gh = shutil.which("gh")
        if not gh or not gh_repo:
            checks.append(check("github_repo", "missing", "gh or BRIDGE_GITHUB_REPO unavailable"))
        else:
            try:
                result = subprocess.run([gh, "repo", "view", gh_repo, "--json", "nameWithOwner"],
                                        capture_output=True, text=True, timeout=15)
                checks.append(check("github_repo", "present" if result.returncode == 0 else "unknown",
                                    "read-only gh repo view; response omitted"))
            except (OSError, subprocess.TimeoutExpired):
                checks.append(check("github_repo", "unknown", "read-only gh query unavailable"))
    else:
        checks.append(check("github_repo", "disabled", "use --check-github to query"))

    checks.append(check("end_to_end", "unknown",
                        "Grok Bot connector and a real handoff have not been verified by this check"))
    print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    optional_cli = {"cli:agy"}
    optional_cli.update("cli:" + name for name, gate in
                        (("grok", "BRIDGE_GROK_ENABLED"), ("cursor", "BRIDGE_CURSOR_ENABLED"))
                        if env.get(gate) != "1")
    blocking = any(c["state"] == "missing" and c["name"] not in optional_cli for c in checks)
    blocking |= any(c["state"] == "unknown" and c["name"] in ("cursor_identity", "github_repo", "launchd")
                    for c in checks)
    return 1 if blocking else 0


def sys_platform_is_macos():
    return sys.platform == "darwin"


if __name__ == "__main__":
    raise SystemExit(main())
