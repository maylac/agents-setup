#!/usr/bin/env python3
"""Publish the mission-hub snapshot to maylac/agent-tasks issue 6.

Reads `mission_hub.py --format json` and, separately, every open
`needs-approval` issue, then rewrites issue 6 with
docs/grok-bot/ops-hub-header.md prefixed. Runs between 07:30 and 07:59 JST
also post a short comment (counts and the approval list) so GitHub emails it.

--input-json reads a fixture instead of calling gh. Shape:
  {"summary": <mission_hub.py --format json output>,
   "approvals": [{"number": 1, "title": "...", "url": "...",
                  "createdAt": "2026-11-01T00:00:00Z"}, ...]}
--dry-run prints the issue body, then the comment body when in the morning
window, and performs no gh calls that write.
"""
import argparse
from datetime import datetime, time, timedelta, timezone
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = "maylac/agent-tasks"
ISSUE = "6"
JST = timezone(timedelta(hours=9), "JST")
HERE = Path(__file__).resolve().parent
HEADER = HERE.parent / "docs" / "grok-bot" / "ops-hub-header.md"
MARKER = "<!-- grokbot-mission-hub:v1 -->"
MORNING_START, MORNING_END = time(7, 30), time(8, 0)
LIST_LIMIT = 1000
APPROVAL_FIELDS = "number,title,url,createdAt"


def parse_now(value):
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def jst(value):
    """ISO string or datetime -> 'YYYY-MM-DD HH:MM JST'; unknown when absent."""
    if not value:
        return "unknown"
    if isinstance(value, str):
        try:
            value = parse_now(value)
        except ValueError:
            return "unknown"
    return value.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")


def is_morning(now):
    return MORNING_START <= now.astimezone(JST).time() < MORNING_END


def run_gh(args):
    return subprocess.run(["gh"] + args, capture_output=True, text=True, check=True).stdout


def decode_pages(text):
    """`gh api --paginate` prints one JSON array per page back to back."""
    decoder, items, index = json.JSONDecoder(), [], 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        page, index = decoder.raw_decode(text, index)
        items.extend(page)
    return items


def fetch_approvals():
    """All open needs-approval issues. gh issue list caps at --limit, so a full
    page falls back to the paginated REST endpoint instead of dropping the rest."""
    listed = json.loads(run_gh(["issue", "list", "-R", REPO, "--state", "open",
                                "--label", "needs-approval", "--limit", str(LIST_LIMIT),
                                "--json", APPROVAL_FIELDS]))
    if len(listed) < LIST_LIMIT:
        return listed
    pages = decode_pages(run_gh(["api", "--paginate",
                                 "repos/%s/issues?state=open&labels=needs-approval&per_page=100" % REPO]))
    return [{"number": p["number"], "title": p.get("title", ""), "url": p.get("html_url", ""),
             "createdAt": p.get("created_at")} for p in pages if "pull_request" not in p]


def fetch_summary(now):
    result = subprocess.run([sys.executable, str(HERE / "mission_hub.py"), "--format", "json",
                             "--repo", REPO, "--limit", str(LIST_LIMIT),
                             "--now", now.isoformat()],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def build(summary, approvals):
    """Fresh open-only view; closed attention entries from history are ignored."""
    def is_open(item):
        return (item.get("state") or "").lower() == "open"

    waiting = sorted({a["number"]: a for a in approvals}.values(), key=lambda a: a["number"])
    return {"waiting": waiting,
            "attention": [i for i in summary.get("attention", []) if is_open(i)],
            "in_flight": [i for i in summary.get("in_flight", []) if is_open(i)]}


def esc(value):
    return str(value).replace("\n", " ").replace("[", "\\[").replace("]", "\\]")


def link(item):
    title = esc(item.get("title", ""))
    url = item.get("url") or ""
    return "[#%s %s](%s)" % (item.get("number"), title, url) if url else "#%s %s" % (item.get("number"), title)


def section(title, rows, detail):
    lines = ["### %s (%d)" % (title, len(rows)), ""]
    lines += ["- %s — %s" % (link(r), detail(r)) for r in rows] or ["なし"]
    return lines + [""]


def approval_lines(view):
    return section("承認待ち", view["waiting"], lambda r: "起票 " + jst(r.get("createdAt")))


def render_body(header, view, now):
    lines = [MARKER, "# 運用ハブ", "", header.rstrip("\n"), "",
             "## 自動集計", "",
             "生成: %s。open の Issue だけを数える。" % jst(now), "",
             "承認待ち %d / 異常 %d / 実行中 %d" % (len(view["waiting"]), len(view["attention"]),
                                              len(view["in_flight"])), ""]
    lines += approval_lines(view)
    lines += section("異常", view["attention"],
                     lambda r: "%s、最終報告 %s" % (r.get("status", "unknown"), jst(r.get("last_report_at"))))
    lines += section("実行中", view["in_flight"],
                     lambda r: "started %s%s" % (jst(r.get("started_at")), "、停止疑い" if r.get("stale") else ""))
    return "\n".join(lines).rstrip("\n") + "\n"


def render_comment(view, now):
    lines = ["運用ハブ朝の集計 (%s)" % jst(now), "",
             "承認待ち %d / 異常 %d / 実行中 %d" % (len(view["waiting"]), len(view["attention"]),
                                              len(view["in_flight"])), ""]
    lines += approval_lines(view)
    return "\n".join(lines).rstrip("\n") + "\n"


def post(kind, body):
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as handle:
        handle.write(body)
    try:
        run_gh(["issue", kind, ISSUE, "-R", REPO, "--body-file", handle.name])
    finally:
        Path(handle.name).unlink()


def phase(cmd):
    """Fixed, secret-free label for a failed child command."""
    cmd = [str(part) for part in (cmd or [])]
    if cmd[:1] == ["gh"]:
        return "gh " + " ".join(cmd[1:3]) if cmd[1:2] == ["issue"] else "gh " + " ".join(cmd[1:2])
    return "mission_hub" if any(part.endswith("mission_hub.py") for part in cmd) else "unknown"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-json", type=Path, help="fixture envelope instead of gh reads")
    parser.add_argument("--now", help="ISO timestamp with timezone (naive = UTC)")
    parser.add_argument("--dry-run", action="store_true", help="print bodies, no gh writes")
    args = parser.parse_args(argv)
    try:
        now = parse_now(args.now)
        if args.input_json:
            data = json.loads(args.input_json.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("summary"), dict) \
                    or not isinstance(data.get("approvals"), list):
                raise ValueError("--input-json must be {summary: {...}, approvals: [...]}")
            summary, approvals = data["summary"], data["approvals"]
        else:
            summary, approvals = fetch_summary(now), fetch_approvals()
        view = build(summary, approvals)
        body = render_body(HEADER.read_text(encoding="utf-8"), view, now)
        comment = render_comment(view, now) if is_morning(now) else None
        if args.dry_run:
            print("===== issue %s body =====" % ISSUE)
            print(body, end="")
            print("===== issue %s comment =====" % ISSUE)
            print(comment if comment else "(skipped: outside 07:30-07:59 JST)", end="" if comment else "\n")
            return 0
        post("edit", body)
        if comment:
            post("comment", comment)
        return 0
    except subprocess.CalledProcessError as exc:
        # Never echo the child's stdout/stderr or argv: gh output can carry tokens.
        print("publish-hub: command failed (phase=%s, returncode=%s)" % (phase(exc.cmd), exc.returncode),
              file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("publish-hub: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
