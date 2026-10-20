#!/usr/bin/env python3
"""Slack -> Mac mini bridge: turns task contracts posted by Dots into agent runs.

Polls one Slack channel (stdlib only, no Socket Mode), accepts top-level
messages only from allowlisted senders, runs `claude -p`, `codex exec` or
`agy --print` in a fresh git worktree of an allowlisted repo, and replies in
the thread.
With BRIDGE_TRANSPORT=github it instead reads open issues labelled
`agent-task` (via the already-authenticated `gh` CLI), replies as issue
comments, and closes the issue; Dots relays results to Slack.

An agent that hits a Hard Stop prints a line starting with NEEDS-APPROVAL:;
the bridge then labels the issue `needs-approval` and leaves it open instead
of closing it. A rate-limit message in the agent output is reported as
"blocked (rate limit)" with the matching line so the dispatcher can relay
the reset time.

Contract format (header lines, blank line, then the task body):

    agent: claude            # or codex / agy
    repo: /Users/me/workspace/project
    model: Gemini 3.5 Flash (Low)   # optional

    <goal, owned files, acceptance criteria, ...>
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import harness

API = "https://slack.com/api/"
REPLY_LIMIT = 3500
AGENTS = ("claude", "codex", "agy", "grok")
APPROVAL_MARK = "NEEDS-APPROVAL:"
RATE_LIMIT_RE = re.compile(r"(?i)(\b429\b|rate.?limit|usage limit|resets? at)")


def load_config(env=os.environ):
    transport = env.get("BRIDGE_TRANSPORT", "slack")
    if transport not in ("slack", "github"):
        raise SystemExit("slack-bridge: BRIDGE_TRANSPORT must be 'slack' or 'github'")
    required = ["BRIDGE_ALLOWED_SENDERS", "BRIDGE_ALLOWED_REPOS"]
    required += ["SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"] if transport == "slack" else ["BRIDGE_GITHUB_REPO"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise SystemExit("slack-bridge: missing config: " + ", ".join(missing))
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
    return {
        "transport": transport,
        "github_repo": env.get("BRIDGE_GITHUB_REPO", ""),
        "github_label": env.get("BRIDGE_GITHUB_LABEL", "agent-task"),
        "token": env.get("SLACK_BOT_TOKEN", ""),
        "channel": env.get("SLACK_CHANNEL_ID", ""),
        "senders": set(split(env["BRIDGE_ALLOWED_SENDERS"])),
        "repos": {os.path.realpath(p) for p in split(env["BRIDGE_ALLOWED_REPOS"])},
        "state": env.get("BRIDGE_STATE_FILE", os.path.expanduser("~/.local/state/slack-bridge/last_ts")),
        "worktrees": env.get("BRIDGE_WORKTREE_DIR", os.path.expanduser("~/.local/state/slack-bridge/worktrees")),
        "interval": int(env.get("BRIDGE_POLL_SECONDS", "20")),
        "timeout": int(env.get("BRIDGE_TASK_TIMEOUT_SECONDS", "3600")),
        "claude_mode": env.get("BRIDGE_CLAUDE_PERMISSION_MODE", "auto"),
        "agy_model": env.get("BRIDGE_AGY_DEFAULT_MODEL", "Gemini 3.5 Flash (Low)"),
        "codex_bin": env.get("BRIDGE_CODEX_BIN", "codex"),
        "grok_enabled": env.get("BRIDGE_GROK_ENABLED", "") == "1",
        "grok_bin": env.get("BRIDGE_GROK_BIN", "grok"),
        "grok_args": shlex.split(env.get("BRIDGE_GROK_ARGS", "--permission-mode acceptEdits")),
        "approval_label": env.get("BRIDGE_APPROVAL_LABEL", "needs-approval"),
        "policy": harness.load_policy(env.get("BRIDGE_ROUTING_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "routing.json"))),
        "cooldowns": env.get("BRIDGE_COOLDOWN_FILE", os.path.expanduser("~/.local/state/slack-bridge/cooldowns.json")),
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
    if header.get("agent") not in AGENTS:
        raise ValueError("agent must be one of: " + ", ".join(AGENTS))
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
    if header["agent"] == "codex":
        cmd = [cfg["codex_bin"], "exec", body, "--sandbox", "workspace-write"]
        if header.get("model"):
            cmd += ["-m", header["model"]]
        return cmd
    if header["agent"] == "grok":
        # Grok Build CLI (SuperGrok / X Premium+ login; grok 1.0.62 flags). Permission mode
        # comes from BRIDGE_GROK_ARGS (default acceptEdits); never a bypass flag.
        cmd = [cfg["grok_bin"], "-p", body] + cfg["grok_args"]
        return cmd + ["-m", header["model"]] if header.get("model") else cmd
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


def classify_output(returncode, output):
    """Map an agent run to a status line the dispatcher can act on."""
    for line in output.splitlines():
        if line.strip().startswith(APPROVAL_MARK):
            return "needs-approval", line.strip()
    if returncode != 0:
        for line in output.splitlines():
            if RATE_LIMIT_RE.search(line):
                return "blocked (rate limit)", line.strip()[:200]
        return "failed (exit %d)" % returncode, ""
    return "done", ""


def run_task(cfg, text, task_id, say):
    """Run one contract; `say(text)` posts a progress or result reply.

    Returns the status string ("done", "failed ...", "needs-approval", ...).
    """
    try:
        header, body = parse_contract(text)
    except ValueError as e:
        say("rejected: %s" % e)
        return "rejected"
    repo = os.path.realpath(os.path.expanduser(header["repo"]))
    if repo not in cfg["repos"]:
        say("rejected: repo not in BRIDGE_ALLOWED_REPOS: %s" % repo)
        return "rejected"
    routes = [r for r in harness.plan_routes(cfg["policy"], header) if r[0] != "grok" or cfg["grok_enabled"]]
    if header["agent"] == "grok" and not cfg["grok_enabled"]:
        say("rejected: agent grok needs BRIDGE_GROK_ENABLED=1")
        return "rejected"
    name = "bridge-" + task_id
    workdir = os.path.join(cfg["worktrees"], name)
    os.makedirs(cfg["worktrees"], exist_ok=True)
    wt = subprocess.run(["git", "-C", repo, "worktree", "add", "-b", name, workdir],
                        capture_output=True, text=True)
    if wt.returncode != 0:
        say("failed: git worktree add\n" + wt.stderr[-1000:])
        return "failed (worktree)"
    cool = harness.Cooldowns(cfg["cooldowns"])
    trail, status, detail, output, used = [], "blocked (no route)", "", "", None
    for route in routes:
        active = cool.active(route)
        if active:
            trail.append("skip %s: %s until %s" % (harness.route_id(route), active["kind"],
                                                  time.strftime("%H:%M", time.localtime(active["until"]))))
            continue
        if used:  # a previous route died mid-run; start the next one from a clean tree
            subprocess.run(["git", "-C", workdir, "reset", "--hard", "-q", "HEAD"], capture_output=True)
            subprocess.run(["git", "-C", workdir, "clean", "-fdq"], capture_output=True)
        used = route
        say("started: %s in %s (branch %s)" % (harness.route_id(route), workdir, name))
        cmd = build_command(dict(header, agent=route[0], model=route[1]), harness.PREAMBLE + body, cfg)
        env = dict(os.environ, CROSS_HARNESS_PEER="1")
        try:
            res = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                                 timeout=cfg["timeout"], env=env)
            output = (res.stdout + ("\n" + res.stderr if res.returncode else "")).strip()
            rc = res.returncode
        except FileNotFoundError:
            rc, output = 127, "command not found: %s" % cmd[0]
            kind = ("binary_missing", output)
        except subprocess.TimeoutExpired:
            status, detail, output = "failed (timeout %ds)" % cfg["timeout"], "", ""
            break
        else:
            kind = None if APPROVAL_MARK in output else harness.unavailable_kind(rc, output)
        if kind:
            cool.mark(route, kind[0], cfg["policy"]["cooldown"][kind[0]], kind[1])
            trail.append("%s unavailable (%s): %s" % (harness.route_id(route), kind[0], kind[1]))
            status, detail = "blocked (no route)", kind[1]
            continue
        status, detail = classify_output(rc, output)
        break
    route_note = ""
    if status == "blocked (no route)":
        detail = "; ".join(trail) or "no route available"
    elif trail:
        route_note = "route: %s\n" % " -> ".join(trail + ["ran %s" % harness.route_id(used)])
    tail = output[-(REPLY_LIMIT - 300):]
    say("%s\n%s%sbranch: %s\n```\n%s\n```" % (status, route_note, detail + "\n" if detail else "", name, tail))
    return status


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
            ts = msg["ts"]
            run_task(cfg, msg.get("text", ""), ts.replace(".", "-"), lambda t, ts=ts: reply(cfg, ts, t))


def gh(*args):
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True, check=True).stdout


def github_tasks(issues, cfg):
    return [i for i in issues if (i.get("author") or {}).get("login") in cfg["senders"]]


def poll_github_once(cfg):
    repo, label = cfg["github_repo"], cfg["github_label"]
    issues = json.loads(gh("issue", "list", "-R", repo, "--label", label, "--state", "open",
                           "--json", "number,body,author", "--limit", "20"))
    for issue in sorted(github_tasks(issues, cfg), key=lambda i: i["number"]):
        num = str(issue["number"])
        # Remove the label first: a crash never re-runs a task.
        gh("issue", "edit", num, "-R", repo, "--remove-label", label)
        say = lambda t, num=num: gh("issue", "comment", num, "-R", repo, "--body", t[:REPLY_LIMIT])
        status = run_task(cfg, issue.get("body", ""), "gh%s-%d" % (num, int(time.time())), say)
        if status == "needs-approval":
            # Leave the issue open for the dispatcher to collect the approval.
            gh("issue", "edit", num, "-R", repo, "--add-label", cfg["approval_label"])
        else:
            gh("issue", "close", num, "-R", repo)


def main():
    cfg = load_config()
    poll = poll_github_once if cfg["transport"] == "github" else poll_once
    while True:
        try:
            poll(cfg)
        except Exception as e:  # keep the daemon alive; launchd logs stderr
            print("slack-bridge: %s" % e, file=sys.stderr, flush=True)
        time.sleep(cfg["interval"])


if __name__ == "__main__":
    main()
