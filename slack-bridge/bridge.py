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
import hashlib
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
AGENTS = ("claude", "codex", "agy", "grok", "cursor")
APPROVAL_MARK = "NEEDS-APPROVAL:"
RATE_LIMIT_RE = re.compile(r"(?i)(\b429\b|rate.?limit|session limit|usage limit|resets? at)")


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
        "cursor_enabled": env.get("BRIDGE_CURSOR_ENABLED", "") == "1",
        "cursor_bin": env.get("BRIDGE_CURSOR_BIN", "cursor-agent"),
        "approval_label": env.get("BRIDGE_APPROVAL_LABEL", "needs-approval"),
        "approval_assignee": env.get("BRIDGE_APPROVAL_ASSIGNEE", "").strip(),
        "approvers": set(split(env.get("BRIDGE_APPROVERS", ""))),
        "scope_file": os.path.expanduser(env.get("BRIDGE_SCOPE_FILE", "~/.local/state/slack-bridge/scopes.json")),
        "policy": harness.load_policy(env.get("BRIDGE_ROUTING_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "routing.json"))),
        "cooldowns": env.get("BRIDGE_COOLDOWN_FILE", os.path.expanduser("~/.local/state/slack-bridge/cooldowns.json")),
    }


def parse_contract(text):
    """Return (header dict, body) or raise ValueError."""
    head, sep, body = text.partition("\n\n")
    head = head.strip()
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
    return header, body


def sender_of(msg):
    return msg.get("user") or msg.get("bot_id") or ""


def is_task(msg, cfg):
    if msg.get("subtype") not in (None, "bot_message"):
        return False
    if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
        return False
    return sender_of(msg) in cfg["senders"]


def build_command(header, body, cfg):
    if header["agent"] == "cursor":
        cmd = [cfg["cursor_bin"], "-p", body, "--output-format", "text"]
        return cmd + ["--model", header["model"]] if header.get("model") else cmd
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


def run_task(cfg, text, task_id, say, existing_workdir=None):
    """Run one contract; `say(text)` posts a progress or result reply.

    Returns the status string ("done", "failed ...", "needs-approval", ...).
    """
    cfg["_last_run_invoked"] = False
    try:
        header, body = parse_contract(text)
    except ValueError as e:
        say("rejected: %s" % e)
        return "rejected"
    repo = os.path.realpath(os.path.expanduser(header["repo"]))
    if repo not in cfg["repos"]:
        say("rejected: repo not in BRIDGE_ALLOWED_REPOS: %s" % repo)
        return "rejected"
    if header["agent"] == "cursor":
        if not cfg["cursor_enabled"]:
            say("rejected: agent cursor needs BRIDGE_CURSOR_ENABLED=1")
            return "rejected"
        try:
            check = subprocess.run([cfg["cursor_bin"], "--help"], capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            say("blocked: Cursor CLI binary not found: %s" % cfg["cursor_bin"])
            return "blocked (no route)"
        except subprocess.TimeoutExpired:
            say("blocked: Cursor CLI --help timed out after 10s")
            return "blocked (no route)"
        help_text = check.stdout + "\n" + check.stderr
        if check.returncode != 0:
            say("blocked: Cursor CLI --help failed (exit %d)" % check.returncode)
            return "blocked (no route)"
        # Cursor's documented CLI is called `agent`; require its own identity and
        # the documented headless flags so an unrelated alias cannot pass as Cursor.
        if not re.search(r"(?i)\bcursor\s+(?:cli|agent)\b", help_text):
            say("rejected: configured binary did not identify itself as Cursor CLI")
            return "rejected"
        if not all(flag in help_text for flag in ("-p", "--output-format")) or not re.search(r"(?i)\btext\b", help_text):
            say("rejected: Cursor CLI does not advertise required print/text options")
            return "rejected"
    if header["agent"] == "cursor":
        routes = [("cursor", header.get("model", ""))]
    else:
        routes = [r for r in harness.plan_routes(cfg["policy"], header) if r[0] != "cursor"]
    routes = [r for r in routes
              if (r[0] != "grok" or cfg["grok_enabled"])
              and (r[0] != "cursor" or cfg["cursor_enabled"])]
    if header["agent"] == "grok" and not cfg["grok_enabled"]:
        say("rejected: agent grok needs BRIDGE_GROK_ENABLED=1")
        return "rejected"
    name = "bridge-" + task_id
    if existing_workdir:
        workdir = existing_workdir
        branch_result = subprocess.run(["git", "-C", workdir, "branch", "--show-current"], capture_output=True, text=True)
        if branch_result.returncode:
            say("blocked (worktree missing)")
            return "blocked (worktree missing)"
        name = branch_result.stdout.strip()
    else:
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
        if used and not existing_workdir:  # never reset a dirty approval worktree
            subprocess.run(["git", "-C", workdir, "reset", "--hard", "-q", "HEAD"], capture_output=True)
            subprocess.run(["git", "-C", workdir, "clean", "-fdq"], capture_output=True)
        used = route
        say("started: %s in %s (branch %s)" % (harness.route_id(route), workdir, name))
        preamble = harness.CURSOR_PREAMBLE if route[0] == "cursor" else harness.PREAMBLE
        cmd = build_command(dict(header, agent=route[0], model=route[1]), preamble + body, cfg)
        env = dict(os.environ, CROSS_HARNESS_PEER="1")
        env.pop("GH_TOKEN", None)
        try:
            res = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                                 timeout=cfg["timeout"], env=env)
            cfg["_last_run_invoked"] = True
            output = (res.stdout + ("\n" + res.stderr if res.returncode else "")).strip()
            rc = res.returncode
        except FileNotFoundError:
            rc, output = 127, "command not found: %s" % cmd[0]
            kind = ("binary_missing", output)
        except subprocess.TimeoutExpired:
            cfg["_last_run_invoked"] = True
            status, detail, output = "failed (timeout %ds)" % cfg["timeout"], "", ""
            break
        else:
            kind = None if APPROVAL_MARK in output else harness.unavailable_kind(rc, output)
        if kind:
            cool.mark(route, kind[0], cfg["policy"]["cooldown"][kind[0]], kind[1])
            trail.append("%s unavailable (%s): %s" % (harness.route_id(route), kind[0], kind[1]))
            status, detail = "blocked (no route)", kind[1]
            if existing_workdir:
                break
            continue
        status, detail = classify_output(rc, output)
        break
    route_note = ""
    if status == "blocked (no route)":
        detail = "; ".join(trail) or "no route available"
    elif trail:
        route_note = "route: %s\n" % " -> ".join(trail + ["ran %s" % harness.route_id(used)])
    tail = output[-(REPLY_LIMIT - 300):]
    if status == "needs-approval":
        say("NEEDS-APPROVAL: %s\nworktree: %s\nbranch: %s" % (detail, workdir, name))
        say("Agent stopped for approval; output follows:\n```\n%s\n```" % tail)
    else:
        say("%s\n%s%sbranch: %s\n```\n%s\n```" % (status, route_note, detail + "\n" if detail else "", name, tail))
    return status


def read_state(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def write_state(path, ts):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
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
    executed = load_scopes(cfg["scope_file"])
    if os.path.exists(cfg["scope_file"]):
        save_scopes(cfg["scope_file"], executed)
    resumed_numbers = set()
    if cfg["approvers"]:
        approvals = list_open_issues(repo, cfg["approval_label"])
        for issue in sorted(approvals, key=lambda i: i["number"]):
            if resume_approved_issue(cfg, issue):
                resumed_numbers.add(int(issue["number"]))
        executed = load_scopes(cfg["scope_file"])
    issues = list_open_issues(repo, label)
    approval_issues = list_open_issues(repo, cfg["approval_label"])
    approval_numbers = {int(i["number"]) for i in approval_issues}
    for issue in sorted(github_tasks(issues, cfg), key=lambda i: i["number"]):
        num = str(issue["number"])
        if int(num) in approval_numbers or int(num) in resumed_numbers:
            continue
        try:
            header, body = parse_contract(issue.get("body", ""))
            scopes = owned_scopes(body, header["repo"])
        except (ValueError, KeyError):
            scopes = []
        if not scopes:
            gh("issue", "edit", num, "-R", repo, "--remove-label", label)
            gh("issue", "comment", num, "-R", repo, "--body", "failed (no owned files)")
            gh("issue", "close", num, "-R", repo)
            continue
        duplicate = find_duplicate(scopes, int(num), approval_issues, executed, cfg)
        if duplicate:
            gh("issue", "edit", num, "-R", repo, "--remove-label", label)
            gh("issue", "comment", num, "-R", repo, "--body", "blocked (duplicate scope #%s)" % duplicate)
            gh("issue", "close", num, "-R", repo)
            continue
        source = source_comment(cfg, issue.get("body", ""))
        if source is False:
            gh("issue", "edit", num, "-R", repo, "--remove-label", label)
            gh("issue", "comment", num, "-R", repo, "--body", "failed (source mismatch)")
            gh("issue", "close", num, "-R", repo)
            continue
        task_body = issue.get("body", "")
        if source is not None:
            task_body += "\n\nSource comment:\n" + source
        # Remove the label first: a crash never re-runs a task.
        gh("issue", "edit", num, "-R", repo, "--remove-label", label)
        say = lambda t, num=num: gh("issue", "comment", num, "-R", repo, "--body", t[:REPLY_LIMIT])
        status = run_task(cfg, task_body, "gh%s-%d" % (num, int(time.time())), say)
        if status == "needs-approval":
            # Leave the issue open for the dispatcher to collect the approval.
            gh("issue", "edit", num, "-R", repo, "--add-label", cfg["approval_label"])
            if cfg["approval_assignee"]:
                gh("issue", "edit", num, "-R", repo, "--add-assignee", cfg["approval_assignee"])
            approval_issues.append(dict(issue, number=int(num)))
        else:
            gh("issue", "close", num, "-R", repo)
            if cfg.get("_last_run_invoked"):
                record_scopes(cfg["scope_file"], int(num), scopes)
                executed = load_scopes(cfg["scope_file"])


def list_open_issues(repo, label):
    path = "repos/%s/issues?state=open&labels=%s&per_page=100" % (repo, urllib.parse.quote(label, safe=""))
    output = gh("api", "--paginate", "--slurp", path)
    items = [item for page in json.loads(output) for item in page if "pull_request" not in item]
    for item in items:
        if "author" not in item and item.get("user"):
            item["author"] = {"login": item["user"].get("login")}
    return items


def save_scopes(path, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(rows, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def owned_scopes(body, repo):
    match = re.search(r"(?im)^Owned files:[ \t]*(.*(?:\n(?!(?:[A-Za-z][A-Za-z0-9 _-]*):).*)*)", body)
    if not match:
        return []
    paths = re.split(r"[,\s]+", match.group(1).strip())
    root = os.path.realpath(os.path.expanduser(repo))
    result = []
    invalid = False
    for path in filter(None, paths):
        if any(char in path for char in "*?["):
            prefix = path[:min((path.find(c) for c in "*?[" if c in path), default=len(path))]
            path = os.path.dirname(prefix) or "."
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
        try:
            if os.path.commonpath((root, full)) != root:
                invalid = True
                continue
        except ValueError:
            invalid = True
            continue
        rel = os.path.relpath(full, root).replace(os.sep, "/")
        if rel != ".." and not rel.startswith("../"):
            result.append((root, rel))
    return [] if invalid else result


def scopes_overlap(left, right):
    for lroot, lp in left:
        for rroot, rp in right:
            lp = "" if lp in ("", ".") else lp.rstrip("/")
            rp = "" if rp in ("", ".") else rp.rstrip("/")
            if lroot == rroot and (lp == rp or not lp or not rp or lp.startswith(rp + "/") or rp.startswith(lp + "/")):
                return True
    return False


def load_scopes(path):
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        return [r for r in rows if time.time() - float(r["recorded"]) <= 86400]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def record_scopes(path, number, scopes):
    rows = [r for r in load_scopes(path) if int(r["number"]) != number]
    rows.append({"number": number, "paths": [root + "/" + p for root, p in scopes], "recorded": time.time()})
    save_scopes(path, rows)


def find_duplicate(scopes, number, approvals, executed, cfg):
    for item in approvals:
        other = int(item["number"])
        if other == number:
            continue
        try:
            h, b = parse_contract(item.get("body", ""))
            other_scopes = owned_scopes(b, h["repo"])
            if other_scopes and scopes_overlap(scopes, other_scopes):
                return other
        except ValueError:
            continue
    for row in executed:
        if int(row["number"]) == number:
            continue
        paths = []
        for p in row.get("paths", []):
            paths.append(os.path.realpath(p))
        for root, rel in scopes:
            absolute = os.path.join(root, rel)
            for p in paths:
                try:
                    common = os.path.commonpath((absolute, p))
                except ValueError:
                    continue
                if common in (absolute, p):
                    return int(row["number"])
    return None


def source_comment(cfg, body):
    head = body.partition("\n\n")[0]
    lines = [line.strip() for line in head.splitlines() if line.strip().lower().startswith("source:")]
    if not lines:
        return None
    match = re.fullmatch(r"source:[ \t]+https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)#issuecomment-(\d+)[ \t]+sha256:([0-9a-f]{64})", lines[0], re.I)
    if len(lines) != 1 or not match:
        return False
    owner, name, issue, comment, expected = match.groups()
    expected = expected.lower()
    endpoint = "repos/%s/%s/issues/comments/%s" % (owner, name, comment)
    result = subprocess.run(["gh", "api", endpoint], capture_output=True)
    if result.returncode:
        return False
    try:
        raw = json.loads(result.stdout)["body"].encode("utf-8")
    except (ValueError, KeyError, TypeError):
        return False
    return raw.decode("utf-8") if hashlib.sha256(raw).hexdigest() == expected else False


def issue_comments(cfg, number):
    output = gh("api", "--paginate", "--slurp", "repos/%s/issues/%s/comments" % (cfg["github_repo"], number))
    return [comment for page in json.loads(output) for comment in page]


def approval_action(comment):
    lines = (comment.get("body") or "").splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].strip().startswith("APPROVED:"):
        return None
    return " ".join([lines[first].strip()[len("APPROVED:"):].strip()] + [line.strip() for line in lines[first + 1:] if line.strip()]).strip()


def resume_approved_issue(cfg, issue):
    num, repo = str(issue["number"]), cfg["github_repo"]
    comments = issue_comments(cfg, num)
    login = gh("api", "user", "--jq", ".login").strip()
    marker = None
    for i, c in enumerate(comments):
        if c.get("user", {}).get("login") == login and (c.get("body") or "").startswith("NEEDS-APPROVAL:"):
            marker = i
    if marker is None:
        return False
    approval = next(((c, approval_action(c)) for c in comments[marker + 1:]
                     if c.get("user", {}).get("login") in cfg["approvers"] and approval_action(c) is not None), None)
    if not approval:
        return False
    comment, action = approval
    if not action:
        _block_resume(cfg, num, "failed (empty approved action)")
        return True
    record = comments[marker].get("body", "")
    workdir = re.search(r"(?m)^worktree: (.+)$", record)
    branch = re.search(r"(?m)^branch: (.+)$", record)
    if not workdir or not branch:
        _block_resume(cfg, num, "blocked (worktree missing)")
        return True
    path = os.path.realpath(workdir.group(1))
    if not path.startswith(os.path.realpath(cfg["worktrees"]) + os.sep):
        _block_resume(cfg, num, "blocked (worktree missing)")
        return True
    try:
        header, body = parse_contract(issue.get("body", ""))
        repo_path = os.path.realpath(os.path.expanduser(header["repo"]))
        if repo_path not in cfg["repos"]:
            raise ValueError()
        if not os.path.isdir(path):
            raise ValueError()
        listed = subprocess.run(["git", "-C", repo_path, "worktree", "list", "--porcelain"], capture_output=True, text=True, check=True).stdout
        records = [block.splitlines() for block in listed.strip().split("\n\n")]
        if not any("worktree %s" % path in rows and "branch refs/heads/%s" % branch.group(1) in rows for rows in records):
            raise ValueError()
    except Exception:
        _block_resume(cfg, num, "blocked (worktree missing)")
        return True
    source = source_comment(cfg, issue.get("body", ""))
    if source is False:
        _block_resume(cfg, num, "failed (source mismatch)")
        return True
    scopes = owned_scopes(body, repo_path)
    if not scopes:
        _block_resume(cfg, num, "failed (no owned files)")
        return True
    executed = load_scopes(cfg["scope_file"])
    approvals = list_open_issues(repo, cfg["approval_label"])
    duplicate = find_duplicate(scopes, int(num), approvals, executed, cfg)
    if duplicate:
        _block_resume(cfg, num, "blocked (duplicate scope #%s)" % duplicate)
        return True
    gh("issue", "edit", num, "-R", cfg["github_repo"], "--remove-label", cfg["approval_label"])
    labels = {label.get("name") if isinstance(label, dict) else label for label in issue.get("labels", [])}
    if cfg["github_label"] in labels:
        gh("issue", "edit", num, "-R", cfg["github_repo"], "--remove-label", cfg["github_label"])
    text = re.sub(r"\A(.*?\n\n)", lambda m: m.group(1) + "Approved action: %s\n\n" % action,
                  issue.get("body", ""), count=1, flags=re.S)
    if source is not None:
        text += "\n\nSource comment:\n" + source
    say = lambda t: gh("issue", "comment", num, "-R", cfg["github_repo"], "--body", t[:REPLY_LIMIT])
    status = run_task(cfg, text, "resume-%s" % num, say, existing_workdir=path)
    if status == "needs-approval":
        gh("issue", "edit", num, "-R", repo, "--add-label", cfg["approval_label"])
        if cfg["approval_assignee"]:
            gh("issue", "edit", num, "-R", repo, "--add-assignee", cfg["approval_assignee"])
    else:
        gh("issue", "close", num, "-R", cfg["github_repo"])
        if cfg.get("_last_run_invoked"):
            record_scopes(cfg["scope_file"], int(num), scopes)
    return True


def _block_resume(cfg, num, message):
    gh("issue", "comment", num, "-R", cfg["github_repo"], "--body", message)
    gh("issue", "close", num, "-R", cfg["github_repo"])


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
