#!/usr/bin/env python3
"""Slack -> Mac mini bridge: turns task contracts posted by Dots into agent runs.

Polls one Slack channel (stdlib only, no Socket Mode), accepts top-level
messages only from allowlisted senders, runs `claude -p` or `agy --print`
in a fresh git worktree of an allowlisted repo, and replies in the thread.

Contract format (header lines, blank line, then the task body):

    agent: claude            # or agy
    repo: /Users/me/workspace/project
    model: Gemini 3.5 Flash (Low)   # optional

    <goal, owned files, acceptance criteria, ...>
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

API = "https://slack.com/api/"
REPLY_LIMIT = 3500


def load_config(env=os.environ):
    required = ["SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID", "BRIDGE_ALLOWED_SENDERS", "BRIDGE_ALLOWED_REPOS"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise SystemExit("slack-bridge: missing config: " + ", ".join(missing))
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
    return {
        "token": env["SLACK_BOT_TOKEN"],
        "channel": env["SLACK_CHANNEL_ID"],
        "senders": set(split(env["BRIDGE_ALLOWED_SENDERS"])),
        "repos": {os.path.realpath(p) for p in split(env["BRIDGE_ALLOWED_REPOS"])},
        "state": env.get("BRIDGE_STATE_FILE", os.path.expanduser("~/.local/state/slack-bridge/last_ts")),
        "worktrees": env.get("BRIDGE_WORKTREE_DIR", os.path.expanduser("~/.local/state/slack-bridge/worktrees")),
        "interval": int(env.get("BRIDGE_POLL_SECONDS", "20")),
        "timeout": int(env.get("BRIDGE_TASK_TIMEOUT_SECONDS", "3600")),
        "claude_mode": env.get("BRIDGE_CLAUDE_PERMISSION_MODE", "auto"),
        "agy_model": env.get("BRIDGE_AGY_DEFAULT_MODEL", "Gemini 3.5 Flash (Low)"),
    }


def parse_contract(text):
    """Return (header dict, body) or raise ValueError."""
    head, sep, body = text.strip().partition("\n\n")
    if not sep or not body.strip():
        raise ValueError("contract needs header lines, a blank line, then the task body")
    header = {}
    for line in head.splitlines():
        key, colon, value = line.partition(":")
        if not colon:
            raise ValueError("bad header line: " + line)
        header[key.strip().lower()] = value.strip()
    if header.get("agent") not in ("claude", "agy"):
        raise ValueError("agent must be 'claude' or 'agy'")
    if not header.get("repo"):
        raise ValueError("repo is required")
    return header, body.strip()


def sender_of(msg):
    return msg.get("user") or msg.get("bot_id") or ""


def is_task(msg, cfg):
    if msg.get("subtype") not in (None, "bot_message"):
        return False
    if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
        return False
    return sender_of(msg) in cfg["senders"]


def build_command(header, body, cfg):
    if header["agent"] == "claude":
        cmd = ["claude", "-p", body, "--permission-mode", cfg["claude_mode"]]
        if header.get("model"):
            cmd += ["--model", header["model"]]
        return cmd
    return ["agy", "--print", body, "--model", header.get("model") or cfg["agy_model"],
            "--mode", "accept-edits", "--print-timeout", "%ds" % cfg["timeout"]]


def slack(cfg, method, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API + method, data=data,
                                 headers={"Authorization": "Bearer " + cfg["token"]})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.load(resp)
    if not out.get("ok"):
        raise RuntimeError("slack %s: %s" % (method, out.get("error")))
    return out


def reply(cfg, ts, text):
    slack(cfg, "chat.postMessage", channel=cfg["channel"], thread_ts=ts, text=text[:REPLY_LIMIT])


def run_task(cfg, msg):
    ts = msg["ts"]
    try:
        header, body = parse_contract(msg.get("text", ""))
    except ValueError as e:
        return reply(cfg, ts, "rejected: %s" % e)
    repo = os.path.realpath(os.path.expanduser(header["repo"]))
    if repo not in cfg["repos"]:
        return reply(cfg, ts, "rejected: repo not in BRIDGE_ALLOWED_REPOS: %s" % repo)
    name = "bridge-" + ts.replace(".", "-")
    workdir = os.path.join(cfg["worktrees"], name)
    os.makedirs(cfg["worktrees"], exist_ok=True)
    wt = subprocess.run(["git", "-C", repo, "worktree", "add", "-b", name, workdir],
                        capture_output=True, text=True)
    if wt.returncode != 0:
        return reply(cfg, ts, "failed: git worktree add\n" + wt.stderr[-1000:])
    reply(cfg, ts, "started: %s in %s (branch %s)" % (header["agent"], workdir, name))
    try:
        res = subprocess.run(build_command(header, body, cfg), cwd=workdir,
                             capture_output=True, text=True, timeout=cfg["timeout"])
        status = "done" if res.returncode == 0 else "failed (exit %d)" % res.returncode
        output = (res.stdout + ("\n" + res.stderr if res.returncode else "")).strip()
    except subprocess.TimeoutExpired:
        status, output = "failed (timeout %ds)" % cfg["timeout"], ""
    tail = output[-(REPLY_LIMIT - 200):]
    reply(cfg, ts, "%s\nbranch: %s\n```\n%s\n```" % (status, name, tail))


def read_state(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def write_state(path, ts):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(ts)


def poll_once(cfg):
    last = read_state(cfg["state"])
    if not last:
        # First run: start from now so old channel history is never executed.
        write_state(cfg["state"], "%.6f" % time.time())
        return
    out = slack(cfg, "conversations.history", channel=cfg["channel"], oldest=last, limit=50)
    for msg in sorted(out.get("messages", []), key=lambda m: float(m["ts"])):
        write_state(cfg["state"], msg["ts"])  # advance first: a crash never re-runs a task
        if is_task(msg, cfg):
            run_task(cfg, msg)


def main():
    cfg = load_config()
    while True:
        try:
            poll_once(cfg)
        except Exception as e:  # keep the daemon alive; launchd logs stderr
            print("slack-bridge: %s" % e, file=sys.stderr, flush=True)
        time.sleep(cfg["interval"])


if __name__ == "__main__":
    main()
