#!/usr/bin/env python3
"""Read-only summary of executable GitHub agent-task issues."""
import argparse
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


STATUSES = ("started", "done", "failed", "blocked", "needs-approval", "rejected")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/\d+(?:#\S*)?$")
AGENT_RE = re.compile(r"(?im)^agent:\s*(?:claude|codex|agy|grok|cursor)\s*$")
CONTRACT_REPO_RE = re.compile(r"(?im)^repo:\s*\S+\s*$")
AGENT_OUTCOME_RE = re.compile(r"^(?:status:\s*(blocked|failed|needs-approval)\b|\*\*状態:\s*(blocked|failed|needs-approval)\s*\*\*)", re.I)


def parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        return None


def labels_of(issue):
    return {item.get("name", "") if isinstance(item, dict) else str(item)
            for item in issue.get("labels", [])}


def is_task(issue):
    labels = labels_of(issue)
    body = issue.get("body") or ""
    header, separator, task_body = body.partition("\n\n")
    executable_contract = bool(separator and task_body.strip() and
                                AGENT_RE.search(header) and CONTRACT_REPO_RE.search(header))
    return "ops-hub" not in labels and ("agent-task" in labels or executable_contract)


def reports(issue):
    found = []
    for comment in issue.get("comments", []):
        body = comment.get("body") or ""
        first = next((line.strip() for line in body.splitlines() if line.strip()), "")
        status = next((s for s in STATUSES if first == s or first.startswith(s + ":")
                       or first.startswith(s + " ")), None)
        if status:
            found.append((parse_time(comment.get("createdAt")), status, first))
    return sorted(found, key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc))


def reported_agent_outcome(issue, final_status):
    """Read only an explicit outcome marker at the start of the latest bridge stdout block."""
    if final_status != "done":
        return None
    final_comments = []
    for comment in issue.get("comments", []):
        body = comment.get("body") or ""
        first = next((line.strip() for line in body.splitlines() if line.strip()), "")
        if first == "done":
            final_comments.append((parse_time(comment.get("createdAt")), body))
    if not final_comments:
        return None
    final_comments.sort(key=lambda entry: entry[0] or datetime.min.replace(tzinfo=timezone.utc))
    body = final_comments[-1][1]
    in_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            if in_fence:
                break
            in_fence = True
            continue
        if in_fence and line.strip():
            match = AGENT_OUTCOME_RE.match(line.strip())
            return (match.group(1) or match.group(2)).lower() if match else None
    return None


def artifact_urls(issue):
    urls = set()
    values = [issue.get("body") or ""]
    values.extend(comment.get("body") or "" for comment in issue.get("comments", []))
    for value in values:
        for url in re.findall(r"https://github\.com/[^\s<>\])]+", value):
            url = url.rstrip(".,;:")
            if GITHUB_URL_RE.fullmatch(url):
                urls.add(url)
    return sorted(urls)


def summarize(issues, now, stale_minutes):
    summary = {"waiting_approval": [], "attention": [], "in_flight": [],
               "completed": [], "active_jobs": [], "ignored_count": 0}
    for issue in issues:
        if not is_task(issue):
            summary["ignored_count"] += 1
            continue
        item = {"number": issue.get("number"), "title": issue.get("title", ""),
                "state": issue.get("state", "unknown"), "url": issue.get("url", ""),
                "last_report_at": None, "status": "unknown", "stale": False,
                "artifacts": []}
        timeline = reports(issue)
        labels = labels_of(issue)
        if timeline:
            report_at, status, _line = timeline[-1]
            item["status"] = status
            item["last_report_at"] = report_at.isoformat() if report_at else None
            item["agent_outcome"] = reported_agent_outcome(issue, status)
        if "needs-approval" in labels or item["status"] == "needs-approval":
            summary["waiting_approval"].append(item)
        if (item["status"] in ("failed", "blocked", "rejected") or
                item.get("agent_outcome") in ("blocked", "failed", "needs-approval")):
            summary["attention"].append(item)
        elif (issue.get("state") or "").lower() == "closed" and item["status"] == "unknown":
            summary["attention"].append(item)
        if (issue.get("state") or "").lower() == "open":
            summary["active_jobs"].append(item)
        started = next((r for r in reversed(timeline) if r[1] == "started"), None)
        final = next((r for r in reversed(timeline) if r[1] != "started"), None)
        if started and (final is None or (final[0] and started[0] and final[0] < started[0])):
            item["stale"] = bool(started[0] and (now - started[0]).total_seconds() > stale_minutes * 60)
            item["started_at"] = started[0].isoformat() if started[0] else None
            summary["in_flight"].append(item)
        if item["status"] == "done":
            done_at = timeline[-1][0]
            verified = False
            if done_at:
                for comment in issue.get("comments", []):
                    at = parse_time(comment.get("createdAt"))
                    first = next((line.strip() for line in (comment.get("body") or "").splitlines()
                                  if line.strip()), "")
                    if at is not None and at > done_at and first.startswith("VERIFIED:"):
                        verified = True
                        break
            item["evidence"] = "dispatcher-recorded" if verified else "pending"
            item["artifacts"] = artifact_urls(issue)
            summary["completed"].append(item)
    for key in ("waiting_approval", "attention", "in_flight", "completed", "active_jobs"):
        summary[key].sort(key=lambda x: x.get("number") or 0)
    return summary


def markdown(summary):
    def esc(value):
        return (str(value).replace("|", "\\|").replace("\n", " ")
                .replace("[", "\\[").replace("]", "\\]").replace("<", "&lt;").replace(">", "&gt;"))

    lines = ["# Mission Hub", "", "Read-only queue snapshot. A later top-level `VERIFIED:` comment is recorded as Dispatcher-reported evidence; the collector does not independently authenticate it.", ""]
    groups = (("Waiting for approval", "waiting_approval"), ("Needs attention", "attention"),
              ("In flight", "in_flight"), ("Completed", "completed"), ("Active jobs", "active_jobs"))
    for title, key in groups:
        rows = summary[key]
        lines += ["## %s (%d)" % (title, len(rows)), ""]
        if not rows:
            lines += ["None", ""]
            continue
        lines += ["| # | Task | Status | Last report | Detail |", "|---:|---|---|---|---|"]
        for row in rows:
            task_url = row.get("url") or ""
            task = "[%s](%s)" % (esc(row.get("title", "")), task_url) if GITHUB_URL_RE.fullmatch(task_url) else esc(row.get("title", ""))
            detail = ("STALE; " if row.get("stale") else "")
            detail += row.get("evidence", "")
            artifact_links = " " + " ".join("[artifact](%s)" % u for u in row.get("artifacts", [])) if row.get("artifacts") else ""
            status = row.get("status", "unknown")
            if row.get("agent_outcome"):
                status += " (agent %s)" % row["agent_outcome"]
            lines.append("| %s | %s | %s | %s | %s%s |" % (row.get("number", ""), task, esc(status), esc(row.get("last_report_at") or "unknown"), esc(detail), artifact_links))
        lines.append("")
    lines.append("Ignored non-task/dashboard entries: %d" % summary["ignored_count"])
    return "\n".join(lines)


def get_issues(repo, limit):
    if not REPO_RE.fullmatch(repo):
        raise ValueError("--repo must be owner/repo")
    if not shutil.which("gh"):
        raise RuntimeError("gh CLI is unavailable")
    result = subprocess.run(["gh", "issue", "list", "--repo", repo, "--state", "all",
                             "--limit", str(limit), "--json",
                             "number,title,body,state,labels,comments,url,updatedAt"],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def validate_issues(issues):
    if not isinstance(issues, list):
        raise ValueError("issue input must be a JSON array")
    for index, issue in enumerate(issues):
        where = "issue[%d]" % index
        if not isinstance(issue, dict):
            raise ValueError(where + " must be an object")
        number = issue.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError(where + ".number must be a positive integer")
        for name in ("title", "body", "state", "url"):
            value = issue.get(name)
            if value is not None and not isinstance(value, str):
                raise ValueError(where + "." + name + " must be a string")
        if "labels" in issue and not isinstance(issue["labels"], list):
            raise ValueError(where + ".labels must be an array")
        for label in issue.get("labels", []):
            if not isinstance(label, (str, dict)) or (isinstance(label, dict) and not isinstance(label.get("name", ""), str)):
                raise ValueError(where + ".labels entries must be strings or named objects")
        if "comments" in issue and not isinstance(issue["comments"], list):
            raise ValueError(where + ".comments must be an array")
        for comment_index, comment in enumerate(issue.get("comments", [])):
            comment_where = "%s.comments[%d]" % (where, comment_index)
            if not isinstance(comment, dict):
                raise ValueError(comment_where + " must be an object")
            if comment.get("body") is not None and not isinstance(comment.get("body"), str):
                raise ValueError(comment_where + ".body must be a string")
            if comment.get("createdAt") is not None and not isinstance(comment.get("createdAt"), str):
                raise ValueError(comment_where + ".createdAt must be a string")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="maylac/agent-tasks")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--stale-minutes", type=int, default=60)
    parser.add_argument("--input-json", type=Path, help="offline fixture instead of gh")
    parser.add_argument("--now", help="ISO timestamp for deterministic snapshots")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.limit <= 1000:
            raise ValueError("--limit must be between 1 and 1000")
        if not 1 <= args.stale_minutes <= 10080:
            raise ValueError("--stale-minutes must be between 1 and 10080")
        if not REPO_RE.fullmatch(args.repo):
            raise ValueError("--repo must be owner/repo")
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if not now:
            raise ValueError("--now must be an ISO timestamp")
        issues = json.loads(args.input_json.read_text(encoding="utf-8")) if args.input_json else get_issues(args.repo, args.limit)
        validate_issues(issues)
        result = summarize(issues, now, args.stale_minutes)
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.format == "json" else markdown(result))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError, RuntimeError) as exc:
        print("mission-hub: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
