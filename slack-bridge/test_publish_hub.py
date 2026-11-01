import contextlib
import io
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

import publish_hub


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "publish-hub.json"
TEMPLATE = HERE.parent / "launchd" / "com.maylac.mission-hub-publish.plist.template"
SENTINEL = "ghp_SENTINEL_do_not_leak_0123456789"

FAKE_GH = """#!%s
import json, os, sys
argv = sys.argv[1:]
d = os.environ["FAKE_GH_DIR"]
entry = {"argv": argv}
if "--body-file" in argv:
    with open(argv[argv.index("--body-file") + 1], encoding="utf-8") as f:
        entry["body"] = f.read()
with open(os.path.join(d, "log.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\\n")
fail = os.path.join(d, "fail")
if os.path.exists(fail) and argv[1:2] == [open(fail, encoding="utf-8").read().strip()]:
    sys.stdout.write("token=" + os.environ.get("FAKE_GH_SECRET", "") + "\\n")
    sys.stderr.write("GH_TOKEN=" + os.environ.get("FAKE_GH_SECRET", "") + "\\n")
    sys.exit(4)
def out(name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        sys.stdout.write(f.read())
if argv[:2] == ["issue", "list"] and "needs-approval" in argv:
    out("approvals.json")
elif argv[:2] == ["issue", "list"]:
    out("issues.json")
elif argv[:1] == ["api"]:
    out("pages.txt")
"""


def approval(number):
    return {"number": number, "title": "approve %d" % number,
            "url": "https://github.com/maylac/agent-tasks/issues/%d" % number,
            "createdAt": "2026-11-01T00:00:00Z"}


class FakeGh:
    def __init__(self, test, approvals, issues=(), pages=""):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        gh = self.dir / "gh"
        gh.write_text(FAKE_GH % sys.executable, encoding="utf-8")
        gh.chmod(0o755)
        (self.dir / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")
        (self.dir / "issues.json").write_text(json.dumps(list(issues)), encoding="utf-8")
        (self.dir / "pages.txt").write_text(pages, encoding="utf-8")
        for key, value in (("PATH", str(self.dir) + os.pathsep + os.environ["PATH"]),
                           ("FAKE_GH_DIR", str(self.dir))):
            old = os.environ.get(key)
            os.environ[key] = value
            test.addCleanup(lambda k=key, v=old: os.environ.pop(k) if v is None else os.environ.__setitem__(k, v))

    def calls(self):
        log = self.dir / "log.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def run(argv, with_err=False):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = publish_hub.main(argv)
    return (code, out.getvalue(), err.getvalue()) if with_err else (code, out.getvalue())


class PublishHubTests(unittest.TestCase):
    def test_morning_window_boundaries_in_jst(self):
        cases = {"2026-11-02T07:29:59+09:00": False, "2026-11-02T07:30:00+09:00": True,
                 "2026-11-02T07:59:59+09:00": True, "2026-11-02T08:00:00+09:00": False,
                 "2026-11-01T22:30:00Z": True, "2026-11-01T22:59:00+00:00": True,
                 "2026-11-01T23:00:00Z": False, "2026-11-01T22:45:00": True,
                 "2026-11-01T18:00:00-05:00": False, "2026-11-01T17:45:00-05:00": True}
        for value, expected in cases.items():
            self.assertEqual(publish_hub.is_morning(publish_hub.parse_now(value)), expected, value)

    def test_dry_run_prints_body_and_comment_without_gh(self):
        fake = FakeGh(self, [])
        code, out = run(["--input-json", str(FIXTURE), "--now", "2026-11-01T22:35:00Z", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(fake.calls(), [])
        body, comment = out.split("===== issue 6 comment =====\n")
        header = (HERE.parent / "docs/grok-bot/ops-hub-header.md").read_text(encoding="utf-8")
        self.assertIn("# 運用ハブ\n\n" + header.rstrip("\n") + "\n\n## 自動集計", body)
        self.assertIn("生成: 2026-11-02 07:35 JST", body)
        self.assertIn("承認待ち 2 / 異常 1 / 実行中 1", body)
        self.assertIn("#54 open blocked task](https://github.com/maylac/agent-tasks/issues/54) — blocked、最終報告 2026-11-02 07:10 JST", body)
        self.assertIn("— started 2026-11-02 07:00 JST", body)
        self.assertIn("#3 old approval](https://github.com/maylac/agent-tasks/issues/3) — 起票 2026-10-21 00:30 JST", body)
        self.assertNotIn("#11 ", body)
        self.assertNotIn("#12 ", body)
        self.assertLess(body.index("#3 old"), body.index("#60 deploy"))
        self.assertTrue(comment.startswith("運用ハブ朝の集計 (2026-11-02 07:35 JST)"))
        self.assertIn("#60 deploy approval", comment)
        self.assertNotIn("#54", comment)

    def test_dry_run_outside_window_skips_comment(self):
        code, out = run(["--input-json", str(FIXTURE), "--now", "2026-11-02T08:00:00+09:00", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("===== issue 6 comment =====\n(skipped: outside 07:30-07:59 JST)\n"))

    def test_live_reads_all_approvals_and_writes_body_and_morning_comment(self):
        full = [approval(n) for n in range(1, publish_hub.LIST_LIMIT + 1)]
        rest = [dict(approval(n), html_url=approval(n)["url"], created_at="2026-11-01T00:00:00Z")
                for n in range(1, 1204)]
        pages = "".join(json.dumps(rest[i:i + 100]) + "\n" for i in range(0, len(rest), 100))
        pages = pages[:-2] + ', {"number": 9999, "pull_request": {}}]\n'
        issues = [{"number": 5077, "title": "old failure", "state": "CLOSED", "labels": [{"name": "agent-task"}],
                   "comments": [{"createdAt": "2026-10-01T00:00:00Z", "body": "failed (exit 1)"}],
                   "url": "https://github.com/maylac/agent-tasks/issues/5077"},
                  {"number": 5078, "title": "running", "state": "OPEN", "labels": [{"name": "agent-task"}],
                   "comments": [{"createdAt": "2026-11-01T22:20:00Z", "body": "started: codex"}],
                   "url": "https://github.com/maylac/agent-tasks/issues/5078"}]
        fake = FakeGh(self, full, issues, pages)
        code, out = run(["--now", "2026-11-02T07:59:00+09:00"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        calls = fake.calls()
        argvs = [c["argv"] for c in calls]
        self.assertIn(["issue", "list", "-R", "maylac/agent-tasks", "--state", "open", "--label",
                       "needs-approval", "--limit", "1000", "--json", "number,title,url,createdAt"], argvs)
        self.assertTrue(any(a[:2] == ["api", "--paginate"] and "labels=needs-approval" in a[2] for a in argvs))
        writes = [c for c in calls if "--body-file" in c["argv"]]
        self.assertEqual([c["argv"][:5] for c in writes],
                         [["issue", "edit", "6", "-R", "maylac/agent-tasks"],
                          ["issue", "comment", "6", "-R", "maylac/agent-tasks"]])
        body, comment = writes[0]["body"], writes[1]["body"]
        self.assertIn("承認待ち 1203 / 異常 0 / 実行中 1", body)
        self.assertIn("#1203 approve 1203", body)
        self.assertNotIn("#9999", body)
        self.assertNotIn("#5077 ", body)
        self.assertIn("#5078 running](https://github.com/maylac/agent-tasks/issues/5078) — started 2026-11-02 07:20 JST", body)
        self.assertTrue(body.startswith(publish_hub.MARKER))
        self.assertIn("## 管理範囲", body)
        self.assertIn("#1203 approve 1203", comment)

    def test_short_list_needs_no_api_and_no_comment_at_eight(self):
        fake = FakeGh(self, [approval(5)])
        code, _out = run(["--now", "2026-11-01T23:00:00Z"])
        self.assertEqual(code, 0)
        argvs = [c["argv"] for c in fake.calls()]
        self.assertFalse(any(a[0] == "api" for a in argvs))
        self.assertEqual([a[1] for a in argvs if "--body-file" in a], ["edit"])

    def test_bad_envelope_fails_without_writes(self):
        fake = FakeGh(self, [])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump([], handle)
        self.addCleanup(os.unlink, handle.name)
        code, _out = run(["--input-json", handle.name])
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls(), [])

    def test_gh_failure_never_leaks_child_output(self):
        for verb, expected in (("edit", "phase=gh issue edit, returncode=4"),
                               ("list", "phase=mission_hub, returncode=")):
            with self.subTest(verb=verb):
                fake = FakeGh(self, [approval(5)])
                (fake.dir / "fail").write_text(verb, encoding="utf-8")
                old = os.environ.get("FAKE_GH_SECRET")
                os.environ["FAKE_GH_SECRET"] = SENTINEL
                self.addCleanup(lambda v=old: os.environ.pop("FAKE_GH_SECRET") if v is None
                                else os.environ.__setitem__("FAKE_GH_SECRET", v))
                code, out, err = run(["--now", "2026-11-01T23:00:00Z"], with_err=True)
                self.assertEqual(code, 2)
                self.assertNotIn(SENTINEL, out + err)
                self.assertIn("publish-hub: command failed (%s" % expected, err)
                self.assertEqual(err.count("\n"), 1)

    def test_decode_pages_concatenated_arrays(self):
        self.assertEqual(publish_hub.decode_pages('[1, 2]\n[3][]\n'), [1, 2, 3])


class LaunchdTemplateTests(unittest.TestCase):
    def setUp(self):
        with TEMPLATE.open("rb") as handle:
            self.plist = plistlib.load(handle)
        self.script = self.plist["ProgramArguments"][2]

    def test_template_parses_and_keeps_home_placeholders(self):
        self.assertEqual(self.plist["Label"], "com.maylac.mission-hub-publish")
        self.assertEqual(self.plist["ProgramArguments"][:2], ["/bin/bash", "-lc"])
        self.assertTrue(self.script.startswith("set -e; set -a; source "))
        self.assertIn('"${GH_TOKEN:?', self.script)
        self.assertLess(self.script.index("GH_TOKEN:?"), self.script.index("exec python3"))
        raw = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("$HOME/.config/slack-bridge/env", raw)
        self.assertNotIn("/Users/", raw)

    def shell(self, env_text):
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, True)
        stub = home / "workspace/maylac/agents-setup/slack-bridge/publish_hub.py"
        stub.parent.mkdir(parents=True)
        stub.write_text("import os\nprint('stub ran token=%s' % bool(os.environ.get('GH_TOKEN')))\n",
                        encoding="utf-8")
        if env_text is not None:
            (home / ".config/slack-bridge").mkdir(parents=True)
            (home / ".config/slack-bridge/env").write_text(env_text, encoding="utf-8")
        env = {"HOME": str(home), "PATH": os.environ["PATH"]}
        return subprocess.run(["/bin/bash", "-c", self.script], env=env, capture_output=True,
                              text=True, timeout=30)

    def test_shell_fails_closed_without_env_file(self):
        result = self.shell(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("stub ran", result.stdout)

    def test_shell_fails_closed_without_gh_token(self):
        for text in ("SLACK_X=1\n", "GH_TOKEN=\n"):
            with self.subTest(text=text):
                result = self.shell(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("stub ran", result.stdout)
                self.assertIn("GH_TOKEN missing from slack-bridge env", result.stderr)

    def test_shell_execs_with_gh_token(self):
        result = self.shell("GH_TOKEN=%s\n" % SENTINEL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "stub ran token=True\n")
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
