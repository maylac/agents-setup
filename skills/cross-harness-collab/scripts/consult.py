#!/usr/bin/env python3
"""Run one bounded Claude/Codex peer consultation or owned-path work call."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any


ROLE_MARKER = (
    "You are a delegated peer; CROSS_HARNESS_PEER=1. Inspect only what is needed "
    "to assess the brief using read-only file tools and, for Codex, necessary "
    "read-only shell inspection. Do not edit files, cause side effects, spawn or "
    "delegate to agents, or call another harness. Return concise actionable findings."
)
WORKER_MARKER = (
    "You are a delegated work agent; CROSS_HARNESS_WORKER=1. Complete only the "
    "assigned task and edit only the declared owned paths. This ownership list is "
    "an instruction-level contract, not a filesystem security boundary. You are "
    "not alone: do not revert others' work. Do not delegate, call another harness, "
    "commit, push, publish, send, deploy, cause unrelated side effects, or weaken "
    "permissions. Return concise changes, tests, and blockers."
)
CLAUDE_MODEL = "claude-opus-5-5"
CODEX_MODEL = "gpt-6-astra"
CODEX_WORK_MODEL = "gpt-6-luna"


def receipt(**fields: Any) -> None:
    print(json.dumps(fields, ensure_ascii=False, separators=(",", ":")))


def parse_claude(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned malformed JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Claude returned a non-object response")
    if data.get("is_error") or str(data.get("subtype", "")).startswith("error"):
        raise ValueError(str(data.get("result") or data.get("subtype") or "Claude error"))
    result = data.get("result")
    if not isinstance(result, str) or not result.strip():
        raise ValueError("Claude returned an empty result")
    model_usage = data.get("modelUsage")
    observed_models = []
    top_model = data.get("model")
    if isinstance(top_model, str):
        observed_models.append(top_model)
    usage = None
    if isinstance(model_usage, dict) and model_usage:
        # Usage bucket keys and canonicalModel are response metadata, not request inference.
        for model_id, details in model_usage.items():
            canonical = details.get("canonicalModel") if isinstance(details, dict) else None
            if isinstance(canonical, str):
                observed_models.append(canonical)
            elif isinstance(model_id, str) and model_id.startswith("claude-"):
                observed_models.append(model_id)
        usage = model_usage
    observed_models = list(dict.fromkeys(observed_models))
    return {
        "result": result.strip(),
        "session_id": data.get("session_id"),
        "observed_model": observed_models[0] if len(observed_models) == 1 else None,
        "observed_models": observed_models,
        "usage": usage,
    }


def parse_codex(raw: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Codex returned malformed JSONL: {exc.msg}") from exc
        if not isinstance(event, dict):
            raise ValueError("Codex returned a non-object event")
        events.append(event)
    if not events:
        raise ValueError("Codex returned no JSON events")
    for event in events:
        if event.get("type") in {"turn.failed", "error"}:
            info = event.get("error") or event.get("message") or event
            raise ValueError(f"Codex reported failure: {info}")
    completed = next((e for e in reversed(events) if e.get("type") == "turn.completed"), None)
    if completed is None:
        raise ValueError("Codex response did not complete a turn")
    messages = []
    final_messages = []
    for event in events:
        if event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(text.strip())
                    if item.get("phase") in {"final", "final_answer"}:
                        final_messages.append(text.strip())
    result = "\n".join(final_messages or messages[-1:])
    if not result:
        # Some CLI versions include the final answer on the completion event.
        result = str(completed.get("last_agent_message") or "").strip()
    if not result:
        raise ValueError("Codex returned an empty final result")
    usage = completed.get("usage")
    model = completed.get("model")
    observed_models = [model] if isinstance(model, str) else []
    return {
        "result": result,
        "thread_id": next((e.get("thread_id") for e in events
                            if e.get("type") == "thread.started"), None),
        "observed_model": observed_models[0] if len(observed_models) == 1 else None,
        "observed_models": observed_models,
        "usage": usage,
    }


def terminate_group(proc: subprocess.Popen[str]) -> None:
    started = time.monotonic()
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass
    # Keep TERM's grace period even if the leader exits after closing inherited pipes;
    # descendants may still be alive inside the process group.
    remaining = 0.5 - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream:
                stream.close()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


class PeerInterrupted(Exception):
    def __init__(self, signum: int):
        self.signum = signum


def exact_model_id(target: str, model: str) -> bool:
    if target == "claude":
        return model.startswith("claude-") and bool(re.search(r"-\d", model))
    return model.startswith("gpt-") and bool(re.search(r"-\d", model))


def validate_owned_paths(cwd: Path, declared: list[str]) -> list[str]:
    if not declared:
        raise ValueError("work mode requires at least one --owned-path")
    owned = []
    for value in declared:
        if not value.strip():
            raise ValueError("owned path must not be empty")
        path = Path(value)
        if path.is_absolute():
            raise ValueError(f"owned path must be relative to --cwd: {value}")
        try:
            resolved = (cwd / path).resolve()
            relative = resolved.relative_to(cwd)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"owned path escapes --cwd or cannot be resolved: {value}") from exc
        owned.append(relative.as_posix() or ".")
    return list(dict.fromkeys(owned))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("claude", "codex"))
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--mode", choices=("consult", "work"), default="consult")
    parser.add_argument("--owned-path", action="append", default=[])
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()
    mode = args.mode
    model = args.model or (
        CLAUDE_MODEL if args.target == "claude" else
        CODEX_WORK_MODEL if mode == "work" else CODEX_MODEL
    )
    effort = args.effort or (
        "medium" if args.target == "claude" else
        "high" if mode == "work" else "low"
    )
    timeout = args.timeout if args.timeout is not None else (600 if mode == "work" else 120)
    started = time.monotonic()
    launched = False
    base = {"mode": mode, "target": args.target, "requested_model": model,
            "effort": effort, "timeout_seconds": timeout if math.isfinite(timeout) else None,
            "owned_paths": args.owned_path}

    def fail(message: str, code: int = 1, **extra: Any) -> int:
        if mode == "work":
            extra.setdefault("partial_changes_possible", launched)
            extra.setdefault("owner_action", (
                "inspect the owned paths before retrying" if launched
                else "correct the work request or setup, then retry"
            ))
        receipt(status="error", **base, error=message, exit_code=code,
                elapsed_seconds=round(time.monotonic() - started, 3), **extra)
        return code if code > 0 else 1

    if os.environ.get("CROSS_HARNESS_PEER") == "1":
        return fail("nested cross-harness consultation is disabled")
    if os.environ.get("CROSS_HARNESS_WORKER") == "1":
        return fail("nested cross-harness work is disabled")
    if not math.isfinite(timeout) or timeout <= 0:
        return fail("timeout must be finite and positive")
    brief = sys.stdin.read().strip()
    if not brief:
        return fail("brief from stdin is empty")
    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        return fail("working directory does not exist")
    if mode == "work":
        try:
            owned_paths = validate_owned_paths(cwd, args.owned_path)
        except ValueError as exc:
            return fail(str(exc))
        base["owned_paths"] = owned_paths
    elif args.owned_path:
        return fail("--owned-path is only valid in work mode")
    cli = shutil.which(args.target)
    if not cli:
        return fail(f"{args.target} CLI is not installed")
    if args.target == "codex":
        cli = str(Path(cli).resolve())
    if mode == "consult":
        prompt = f"{ROLE_MARKER}\n\nBRIEF\n{brief}"
    else:
        paths = "\n".join(f"- {path}" for path in base["owned_paths"])
        prompt = (f"{WORKER_MARKER}\n\nOWNED PATHS\n{paths}\n\nTASK\n{brief}")
    if args.target == "claude":
        tools = "Read,Glob,Grep" if mode == "consult" else "Read,Glob,Grep,Edit,Write,Bash"
        permission_mode = "dontAsk" if mode == "consult" else "acceptEdits"
        command = [cli, "-p", "--output-format", "json", "--model", model,
                   "--effort", effort, "--permission-mode", permission_mode,
                   "--permission-prompts", "none", "--tools", tools, "--allowedTools", tools,
                   "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                   "--max-budget-usd", "1.00" if mode == "consult" else "5.00",
                   "--no-session-persistence", "--safe-mode", "--setting-sources", ""]
        child_input = prompt
    else:
        sandbox = "read-only" if mode == "consult" else "workspace-write"
        command = [
            cli, "exec", "--json", "--sandbox", sandbox, "--model", model,
            "--config", f"model_reasoning_effort={effort}", "--config", "project_doc_max_bytes=0",
            "--disable", "hooks", "--ephemeral", "--skip-git-repo-check",
            "--ignore-user-config", "--ignore-rules", "-",
        ]
        child_input = prompt
    env = os.environ.copy()
    if mode == "consult":
        env["CROSS_HARNESS_PEER"] = "1"
        env.pop("CROSS_HARNESS_WORKER", None)
    else:
        env["CROSS_HARNESS_WORKER"] = "1"
        env.pop("CROSS_HARNESS_PEER", None)
    if args.target == "codex":
        executable_dir = str(Path(cli).parent)
        env["PATH"] = os.pathsep.join((executable_dir, env.get("PATH", "")))
    try:
        proc = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
    except OSError as exc:
        return fail(f"could not start {args.target}: {exc}")
    launched = True
    watched_signals = [signal.SIGTERM, signal.SIGINT]
    if hasattr(signal, "SIGHUP"):
        watched_signals.append(signal.SIGHUP)
    def interrupt(signum: int, _frame: Any) -> None:
        raise PeerInterrupted(signum)

    previous_handlers = {sig: signal.signal(sig, interrupt) for sig in watched_signals}
    try:
        stdout, stderr = proc.communicate(input=child_input, timeout=timeout)
    except subprocess.TimeoutExpired:
        for sig in watched_signals:
            signal.signal(sig, signal.SIG_IGN)
        terminate_group(proc)
        return fail(f"{args.target} timed out", 124)
    except (PeerInterrupted, KeyboardInterrupt) as exc:
        for sig in watched_signals:
            signal.signal(sig, signal.SIG_IGN)
        terminate_group(proc)
        interrupted_by = exc.signum if isinstance(exc, PeerInterrupted) else signal.SIGINT
        return fail(f"{args.target} interrupted by signal {interrupted_by}",
                    128 + interrupted_by)
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
    elapsed = round(time.monotonic() - started, 3)
    if proc.returncode != 0:
        detail = stderr.strip().replace("\n", " ")[:600]
        return fail(f"{args.target} exited {proc.returncode}" + (f": {detail}" if detail else ""),
                    proc.returncode if proc.returncode > 0 else 1)
    try:
        parsed = parse_claude(stdout) if args.target == "claude" else parse_codex(stdout)
    except ValueError as exc:
        return fail(str(exc), 1)
    observed_models = parsed["observed_models"]
    model_verified = parsed["observed_model"] == model
    parsed["model_verified"] = model_verified
    if exact_model_id(args.target, model) and observed_models and model not in observed_models:
        return fail("served model does not match the explicitly requested model", 1,
                    observed_model=parsed["observed_model"], observed_models=observed_models,
                    model_verified=False)
    if mode == "work":
        receipt(status="returned", **base, **parsed, task_verified=False,
                owner_action="inspect the owned paths and run the task acceptance checks",
                exit_code=0, elapsed_seconds=elapsed)
    else:
        receipt(status="success", **base, **parsed, exit_code=0, elapsed_seconds=elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
