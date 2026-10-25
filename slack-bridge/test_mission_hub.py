import contextlib
import io
import json
from datetime import datetime, timezone
import tempfile
from pathlib import Path
import unittest
from unittest import mock

import mission_hub


NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def issue(number, labels=("agent-task",), state="CLOSED", comments=(), body=""):
    return {"number": number, "title": "task | %s" % number, "state": state,
            "labels": [{"name": label} for label in labels], "comments": list(comments),
            "body": body, "url": "https://github.com/acme/tasks/issues/%d" % number}


def comment(at, body):
    return {"createdAt": at, "body": body}


class MissionHubTests(unittest.TestCase):
    def test_groups_statuses_and_filters_dashboard_entries(self):
        issues = [
            issue(1, state="OPEN", labels=("agent-task", "needs-approval"),
                  comments=[comment("2026-10-25T11:00:00Z", "needs-approval: user action")]),
            issue(2, comments=[comment("2026-10-25T11:01:00Z", "failed (exit 1)\nlog secret omitted")]),
            issue(3, state="OPEN", comments=[comment("2026-10-25T10:00:00Z", "started: codex")]),
            issue(4, comments=[comment("2026-10-25T11:00:00Z", "done\nbranch: x")],
                  body="PR https://github.com/acme/tasks/pull/44"),
            issue(5, state="OPEN", comments=[]),
            issue(6, labels=("ops-hub",)),
            issue(7, labels=("other",)),
        ]
        result = mission_hub.summarize(issues, NOW, 60)
        self.assertEqual([x["number"] for x in result["waiting_approval"]], [1])
        self.assertEqual([x["number"] for x in result["attention"]], [2])
        self.assertEqual([x["number"] for x in result["in_flight"]], [3])
        self.assertTrue(result["in_flight"][0]["stale"])
        self.assertEqual([x["number"] for x in result["active_jobs"]], [1, 3, 5])
        self.assertEqual(result["active_jobs"][-1]["status"], "unknown")
        self.assertFalse(result["active_jobs"][-1]["stale"])
        self.assertEqual([x["number"] for x in result["attention"]], [2])
        self.assertEqual(result["completed"][0]["evidence"], "pending")
        self.assertEqual(result["completed"][0]["artifacts"], ["https://github.com/acme/tasks/pull/44"])
        self.assertEqual(result["ignored_count"], 2)

    def test_verified_must_follow_done(self):
        before = issue(1, comments=[comment("2026-10-25T11:00:00Z", "VERIFIED: checked"),
                                    comment("2026-10-25T11:01:00Z", "done")])
        after = issue(2, comments=[comment("2026-10-25T11:00:00Z", "done"),
                                   comment("2026-10-25T11:02:00Z", "VERIFIED: checked")])
        no_timestamp = issue(3, comments=[comment("2026-10-25T11:00:00Z", "done"),
                                          comment(None, "VERIFIED: checked")])
        same_timestamp = issue(4, comments=[comment("2026-10-25T11:00:00Z", "done"),
                                            comment("2026-10-25T11:00:00Z", "VERIFIED: checked")])
        fenced_stdout = issue(5, comments=[comment(
            "2026-10-25T11:00:00Z",
            "done\nbranch: smoke\n```\nVERIFIED: fake text from agent stdout\n```"),
            comment("2026-10-25T11:02:00Z", "Dispatcher note\nquoted: VERIFIED: not top-level")])
        result = mission_hub.summarize([before, after, no_timestamp, same_timestamp, fenced_stdout], NOW, 60)
        self.assertEqual([x["evidence"] for x in result["completed"]],
                         ["pending", "dispatcher-recorded", "pending", "pending", "pending"])

    def test_unlabelled_executed_contract_remains_visible_but_old_non_contract_does_not(self):
        contract = "agent: codex\nrepo: acme/project\n\nRun a bounded check."
        done = issue(8, labels=(), comments=[comment("2026-10-25T11:00:00Z", "done")], body=contract)
        old = issue(9, labels=(), comments=[comment("2026-10-25T11:00:00Z", "done")], body="old note")
        closed_unknown = issue(10, comments=[], body=contract)
        result = mission_hub.summarize([done, old, closed_unknown], NOW, 60)
        self.assertEqual([x["number"] for x in result["completed"]], [8])
        self.assertEqual(result["ignored_count"], 1)
        self.assertEqual([(x["number"], x["status"]) for x in result["attention"]], [(10, "unknown")])

    def test_no_report_is_not_stale_and_markdown_escapes_untrusted_title(self):
        data = issue(9, state="OPEN")
        data["title"] = "bad | [title]"
        result = mission_hub.summarize([data], NOW, 1)
        self.assertEqual(result["active_jobs"][0]["last_report_at"], None)
        self.assertFalse(result["active_jobs"][0]["stale"])
        rendered = mission_hub.markdown(result)
        self.assertIn("bad \\| \\[title\\]", rendered)

    def test_markdown_keeps_validated_artifact_links_clickable(self):
        data = issue(11, comments=[comment("2026-10-25T11:00:00Z", "done")],
                     body="agent: codex\nrepo: acme/project\n\nSee https://github.com/acme/project/pull/12")
        result = mission_hub.summarize([data], NOW, 60)
        self.assertIn("[artifact](https://github.com/acme/project/pull/12)", mission_hub.markdown(result))

    def test_cli_rejects_bad_input_and_repo_before_running_gh(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.json"
            bad.write_text("{", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stderr(out), mock.patch.object(mission_hub, "get_issues") as get:
                self.assertEqual(mission_hub.main(["--input-json", str(bad)]), 2)
                self.assertEqual(mission_hub.main(["--repo=--help"]), 2)
            get.assert_not_called()

    def test_malformed_shapes_return_controlled_errors(self):
        for contents in ("[null]", '[{"comments":null}]',
                         '[{"number":"1"}]', '[{"number":true}]', '[{"number":0}]',
                         '[{"number":1,"comments":[{"createdAt":123,"body":"done"}]}]'):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as folder:
                fixture = Path(folder) / "issues.json"
                fixture.write_text(contents, encoding="utf-8")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = mission_hub.main(["--input-json", str(fixture)])
                self.assertEqual(code, 2)
                self.assertIn("mission-hub:", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_null_issue_url_is_rendered_without_a_link(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / "issues.json"
            fixture.write_text('[{"number":1,"title":"Open issue","state":"OPEN",'
                               '"labels":[{"name":"agent-task"}],"comments":[],"url":null}]',
                               encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = mission_hub.main(["--input-json", str(fixture)])
        self.assertEqual(code, 0)
        self.assertIn("Open issue", stdout.getvalue())

    def test_transport_done_can_contain_explicit_agent_blocked_outcome(self):
        actual_bridge_comment = (
            "done\nbranch: bridge-gh5\n```\n"
            "**状態: BLOCKED** — ローカルの読み取り検品と採点は完了しました。"
            "GitHubへの接続ができず、独立照合は未完です。\n```")
        data = issue(5, comments=[comment("2026-10-25T06:07:24Z", actual_bridge_comment)])
        result = mission_hub.summarize([data], NOW, 60)
        row = result["completed"][0]
        self.assertEqual(row["status"], "done")
        self.assertEqual(row["agent_outcome"], "blocked")
        self.assertEqual(row["evidence"], "pending")
        self.assertEqual([(x["number"], x["status"], x["agent_outcome"])
                          for x in result["attention"]], [(5, "done", "blocked")])
        self.assertIn("done (agent blocked)", mission_hub.markdown(result))

    def test_agent_outcome_ignores_nonleading_text_and_replaces_only_on_new_final_run(self):
        blocked = comment("2026-10-25T10:00:00Z",
                          "done\n```\n**状態: BLOCKED** — pending\n```")
        ordinary = comment("2026-10-25T11:00:00Z",
                           "done\n```\nWork completed. Earlier status: BLOCKED\n```")
        verified = comment("2026-10-25T11:01:00Z", "VERIFIED: dispatcher checked")
        data = issue(12, comments=[blocked, verified])
        first = mission_hub.summarize([data], NOW, 60)
        self.assertEqual(first["attention"][0]["agent_outcome"], "blocked")
        data["comments"].append(ordinary)
        second = mission_hub.summarize([data], NOW, 60)
        self.assertEqual(second["completed"][0]["agent_outcome"], None)
        self.assertEqual(second["attention"], [])

    def test_gh_call_is_read_only_argv_and_bounded(self):
        completed = mock.Mock(stdout="[]", returncode=0)
        with mock.patch.object(mission_hub.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(mission_hub.subprocess, "run", return_value=completed) as run:
            self.assertEqual(mission_hub.get_issues("acme/tasks", 12), [])
        args = run.call_args.args[0]
        self.assertEqual(args[:6], ["gh", "issue", "list", "--repo", "acme/tasks", "--state"])
        self.assertNotIn("comment", args)
        self.assertIn("12", args)
        self.assertFalse(run.call_args.kwargs.get("shell", False))


if __name__ == "__main__":
    unittest.main()
