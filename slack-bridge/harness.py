"""Shared harness for every dispatched agent: one preamble, one routing policy.

The bridge asks this module (a) what to prepend to every task so Claude Code,
Codex and Antigravity follow the same rules, (b) which agent/model routes to
try, in order, and (c) whether a failed run means "route unavailable" (fall
back to the next route) or "task failed" (stop and report). Fallbacks are never
silent: the bridge lists every hop in the result comment.
"""
import json
import os
import re
import time

PREAMBLE = """\
[dispatched run] Follow ~/AGENTS.md (Hard Stops, Core Principles) and this repo's AGENTS.md.
- Stay inside the owned files; do not re-scope. Do not delegate to another harness.
- Hard Stop (force push, irreversible deletion, payments/credentials, publishing, prod deploy, daemon restart): do not do it; print one line starting with NEEDS-APPROVAL: and the exact action, then stop.
- Commit on the current branch. Run the acceptance checks; stop when they pass; after two failed approaches stop and report blocked.
- Final message: status, changed files, each check command pass/fail, commit/PR link, notes (max 5 lines). No transcripts or full diffs.

Task:
"""

CURSOR_PREAMBLE = """\
[dispatched read-only review] Analyze the assigned source and return findings in text.
- Read files and source only. Do not edit, create, delete, commit, or publish files.
- Do not delegate or perform actions outside this bounded review.
- Report concrete findings with file and line references, or say none were found.

Task:
"""

# Order matters: the first matching kind wins. Applied to the output tail of a non-zero exit only.
UNAVAILABLE = (
    ("rate_limit", re.compile(r"(?i)(\b429\b|rate.?limit|session limit|usage limit|quota|resets? at)")),
    ("auth", re.compile(r"(?i)(not logged in|not signed in|grok login|/login\b|\b401\b|unauthori[sz]ed|invalid api key|authentication (failed|required))")),
    ("model_unavailable", re.compile(r"(?i)(overloaded|\b529\b|\b503\b|model.{0,40}(not found|not available|does not exist|unsupported)|no access to model)")),
)
TAIL_LINES = 30
DEFAULT_COOLDOWN = {"rate_limit": 1800, "auth": 3600, "model_unavailable": 900, "binary_missing": 3600}


def route_id(route):
    return "%s:%s" % route if route[1] else route[0]


def parse_route(text):
    agent, _, model = text.partition(":")
    return agent.strip(), model.strip()


def load_policy(path):
    with open(path) as f:
        raw = json.load(f)
    chains = {}
    for agent, routes in raw["chains"].items():
        chain = [parse_route(r) for r in routes]
        if not chain or chain[0][0] != agent:
            raise SystemExit("harness: chain for %r must start with an %r route" % (agent, agent))
        chains[agent] = chain
    return {"chains": chains, "cooldown": dict(DEFAULT_COOLDOWN, **raw.get("cooldown_seconds", {}))}


def plan_routes(policy, header):
    """Ordered routes to try. An explicit `model:` or `fallback: off` pins the run to one route."""
    agent = header["agent"]
    chain = list(policy["chains"][agent])
    allow = header.get("fallback", "").lower()
    if header.get("model"):
        chain[0] = (agent, header["model"])
    if allow == "off" or (header.get("model") and allow != "allow"):
        return chain[:1]
    seen, routes = set(), []
    for r in chain:
        if r not in seen:
            seen.add(r)
            routes.append(r)
    return routes


def unavailable_kind(returncode, output):
    """Return (kind, matching line) when a non-zero exit means the route itself is unusable."""
    if returncode == 0:
        return None
    for line in reversed(output.splitlines()[-TAIL_LINES:]):
        for kind, rx in UNAVAILABLE:
            if rx.search(line):
                return kind, line.strip()[:200]
    return None


class Cooldowns:
    """Routes that recently reported themselves unavailable; skipped until `until` (epoch)."""

    def __init__(self, path, clock=time.time):
        self.path, self.clock = path, clock

    def _load(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except (FileNotFoundError, ValueError):
            return {}

    def active(self, route):
        entry = self._load().get(route_id(route))
        if entry and entry["until"] > self.clock():
            return entry
        return None

    def mark(self, route, kind, seconds, detail=""):
        data = {k: v for k, v in self._load().items() if v["until"] > self.clock()}
        data[route_id(route)] = {"until": self.clock() + seconds, "kind": kind, "detail": detail}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)
