import os
import unittest

import bridge

ENV = {
    "SLACK_BOT_TOKEN": "xoxb-test",
    "SLACK_CHANNEL_ID": "C1",
    "BRIDGE_ALLOWED_SENDERS": "U_ME, B_DOTS",
    "BRIDGE_ALLOWED_REPOS": "/tmp",
}


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.cfg = bridge.load_config(ENV)

    def test_missing_config_fails_closed(self):
        with self.assertRaises(SystemExit):
            bridge.load_config({"SLACK_BOT_TOKEN": "x"})

    def test_parse_contract(self):
        header, body = bridge.parse_contract("agent: agy\nrepo: /tmp\n\nlist files")
        self.assertEqual(header, {"agent": "agy", "repo": "/tmp"})
        self.assertEqual(body, "list files")

    def test_parse_rejects_bad_agent_and_missing_body(self):
        for text in ["agent: bash\nrepo: /tmp\n\nx", "agent: claude\nrepo: /tmp", "agent: claude\n\nx"]:
            with self.assertRaises(ValueError):
                bridge.parse_contract(text)

    def test_only_allowlisted_top_level_messages(self):
        self.assertTrue(bridge.is_task({"ts": "1", "user": "U_ME"}, self.cfg))
        self.assertTrue(bridge.is_task({"ts": "1", "bot_id": "B_DOTS", "subtype": "bot_message"}, self.cfg))
        self.assertFalse(bridge.is_task({"ts": "1", "user": "U_OTHER"}, self.cfg))
        self.assertFalse(bridge.is_task({"ts": "2", "thread_ts": "1", "user": "U_ME"}, self.cfg))
        self.assertFalse(bridge.is_task({"ts": "1", "user": "U_ME", "subtype": "channel_join"}, self.cfg))

    def test_build_command_never_bypasses_permissions(self):
        claude = bridge.build_command({"agent": "claude"}, "task", self.cfg)
        codex = bridge.build_command({"agent": "codex", "model": "gpt-6-luna"}, "task", self.cfg)
        agy = bridge.build_command({"agent": "agy"}, "task", self.cfg)
        self.assertEqual(claude[:5], ["claude", "-p", "task", "--permission-mode", "auto"])
        self.assertEqual(codex, ["codex", "exec", "task", "--sandbox", "workspace-write", "-m", "gpt-6-luna"])
        self.assertIn("Gemini 3.5 Flash (Low)", agy)
        for cmd in (claude, codex, agy):
            self.assertNotIn("bypassPermissions", cmd)
            self.assertNotIn("--dangerously-skip-permissions", cmd)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
            self.assertNotIn("danger-full-access", cmd)

    def test_codex_binary_override(self):
        cfg = bridge.load_config(dict(ENV, BRIDGE_CODEX_BIN="/opt/codex-cli/bin/codex"))
        self.assertEqual(bridge.build_command({"agent": "codex"}, "t", cfg)[0], "/opt/codex-cli/bin/codex")
        self.assertEqual(bridge.parse_contract("agent: codex\nrepo: /tmp\n\nx")[0]["agent"], "codex")

    def test_classify_output(self):
        self.assertEqual(bridge.classify_output(0, "all good"), ("done", ""))
        self.assertEqual(bridge.classify_output(1, "boom")[0], "failed (exit 1)")
        status, detail = bridge.classify_output(1, "error: 429 rate limit, resets at 17:10 JST")
        self.assertEqual(status, "blocked (rate limit)")
        self.assertIn("17:10", detail)
        status, detail = bridge.classify_output(0, "did work\nNEEDS-APPROVAL: force push to master\n")
        self.assertEqual((status, detail), ("needs-approval", "NEEDS-APPROVAL: force push to master"))

    def test_github_transport_config(self):
        env = {"BRIDGE_TRANSPORT": "github", "BRIDGE_ALLOWED_SENDERS": "maylac", "BRIDGE_ALLOWED_REPOS": "/tmp"}
        with self.assertRaises(SystemExit):
            bridge.load_config(env)
        cfg = bridge.load_config(dict(env, BRIDGE_GITHUB_REPO="maylac/agent-tasks"))
        self.assertEqual((cfg["transport"], cfg["github_label"]), ("github", "agent-task"))

    def test_github_tasks_only_from_allowlisted_authors(self):
        issues = [{"number": 1, "author": {"login": "U_ME"}}, {"number": 2, "author": {"login": "stranger"}},
                  {"number": 3, "author": None}]
        self.assertEqual([i["number"] for i in bridge.github_tasks(issues, self.cfg)], [1])

    def test_repo_allowlist_uses_realpath(self):
        self.assertIn(os.path.realpath("/tmp"), self.cfg["repos"])


if __name__ == "__main__":
    unittest.main()
