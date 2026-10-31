#!/usr/bin/env python3
"""Refuse agent work from download-style directories and unsafe settings changes.

Handles UserPromptSubmit, PreToolUse and ConfigChange. Standard library only.
This is a policy tripwire, not an OS sandbox; see docs/agent-download-defense.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTRUCTION_NAME = re.compile(
    r"^(agents|agents\.override|claude|claude\.local)(\s*\(\d+\)|[ -]\d+)?\.md$",
    re.IGNORECASE,
)
FILE_TOOLS = {"Read", "Edit", "Write", "MultiEdit"}
WRITE_TOOLS = {"Edit", "Write", "MultiEdit"}
BLOCKED_ENV = {
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
}


def variants(path: Path) -> set[Path]:
    """Lexical absolute form plus symlink-resolved form."""
    lexical = Path(os.path.normpath(path))
    return {lexical, lexical.resolve()}


def home() -> Path:
    return Path(os.path.expanduser("~"))


def untrusted_roots() -> set[Path]:
    h = home()
    return variants(h / "Downloads") | variants(h / "Desktop")


def under(path: Path, roots: set[Path]) -> bool:
    return any(path == r or r in path.parents for r in roots)


def unsafe_cwd(cwd: Any) -> str | None:
    if not isinstance(cwd, str) or not cwd or not os.path.isdir(cwd):
        return "working directory is missing or invalid"
    exact = variants(home()) | variants(Path("/tmp")) | variants(Path("/private/tmp"))
    for p in variants(Path(cwd)):
        if p in exact:
            return "working directory is HOME or the /tmp root"
        if under(p, untrusted_roots()):
            return "working directory is under ~/Downloads or ~/Desktop"
    return None


def target_paths(cwd: Any, file_path: Any) -> set[Path]:
    if not isinstance(file_path, str) or not file_path:
        return set()
    p = Path(os.path.expanduser(file_path))
    if not p.is_absolute():
        p = Path(cwd if isinstance(cwd, str) else os.getcwd()) / p
    return variants(p)


def protected_config(p: Path) -> bool:
    h = home()
    if p in variants(h / ".codex" / "config.toml"):
        return True
    return p.parent.name == ".claude" and re.fullmatch(r"settings.*\.json", p.name) is not None


def pre_tool_reason(data: dict[str, Any]) -> str | None:
    cwd = data.get("cwd")
    reason = unsafe_cwd(cwd)
    if reason:
        return reason
    tool = data.get("tool_name")
    if tool not in FILE_TOOLS:
        return None
    tool_input = data.get("tool_input") or {}
    paths = target_paths(cwd, tool_input.get("file_path") if isinstance(tool_input, dict) else None)
    roots = untrusted_roots()
    for p in paths:
        if under(p, roots) and INSTRUCTION_NAME.match(p.name):
            return "agent instruction file under ~/Downloads or ~/Desktop"
        if tool in WRITE_TOOLS and protected_config(p):
            return "agent settings/config edits must be made and reviewed outside the agent"
    return None


def settings_reason(data: dict[str, Any]) -> str | None:
    if data.get("source") == "skills":
        return None
    paths = target_paths(data.get("cwd"), data.get("file_path"))
    path = next((p for p in paths if p.is_file()), None)
    if path is None or path.suffix.lower() != ".json":
        return None
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "changed settings file is not valid JSON"
    if not isinstance(settings, dict):
        return "changed settings file is not a JSON object"
    env = settings.get("env")
    if isinstance(env, dict):
        hits = sorted(k for k in env if isinstance(k, str) and k.upper() in BLOCKED_ENV)
        if hits:
            return "settings env sets endpoint/credential/proxy keys: " + ", ".join(hits)
    if "apiKeyHelper" in settings:
        return "settings set apiKeyHelper"
    if settings.get("disableAllHooks"):
        return "settings set disableAllHooks"
    perms = settings.get("permissions")
    if isinstance(perms, dict) and perms.get("defaultMode") == "bypassPermissions":
        return "settings set permissions.defaultMode=bypassPermissions"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError
    except Exception:
        print("untrusted-directory-guard: unreadable hook input", file=sys.stderr)
        return 2
    event = data.get("hook_event_name")
    prefix = "untrusted-directory-guard: "
    if event == "UserPromptSubmit":
        reason = unsafe_cwd(data.get("cwd"))
        if reason:
            print(json.dumps({"decision": "block", "reason": prefix + reason + "; start the agent in a reviewed workspace"}))
    elif event == "PreToolUse":
        reason = pre_tool_reason(data)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": prefix + reason,
            }}))
    elif event == "ConfigChange":
        reason = settings_reason(data)
        if reason:
            print(json.dumps({"decision": "block", "reason": prefix + reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
