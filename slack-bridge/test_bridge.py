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
        agy = bridge.build_command({"agent": "agy"}, "task", self.cfg)
        self.assertEqual(claude[:5], ["claude", "-p", "task", "--permission-mode", "auto"])
        self.assertIn("Gemini 3.5 Flash (Low)", agy)
        for cmd in (claude, agy):
            self.assertNotIn("bypassPermissions", cmd)
            self.assertNotIn("--dangerously-skip-permissions", cmd)

    def test_repo_allowlist_uses_realpath(self):
        self.assertIn(os.path.realpath("/tmp"), self.cfg["repos"])


if __name__ == "__main__":
    unittest.main()
