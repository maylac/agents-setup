import json
import os
import shlex
import stat
import subprocess
import tempfile
import unittest

import harness

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
        status, detail = bridge.classify_output(1, "You've hit your session limit · resets 2:50pm (Asia/Tokyo)")
        self.assertEqual(status, "blocked (rate limit)")
        self.assertIn("resets 2:50pm", detail)
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


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.cfg = bridge.load_config(ENV)

    def test_plan_routes_default_and_pinned(self):
        pol = self.cfg["policy"]
        self.assertEqual([r[0] for r in harness.plan_routes(pol, {"agent": "claude"})], ["claude", "claude", "codex", "grok"])
        self.assertEqual(harness.plan_routes(pol, {"agent": "claude", "model": "x"}), [("claude", "x")])
        self.assertEqual(len(harness.plan_routes(pol, {"agent": "claude", "fallback": "off"})), 1)
        self.assertEqual(harness.plan_routes(pol, {"agent": "claude", "model": "x", "fallback": "allow"})[0], ("claude", "x"))
        self.assertGreater(len(harness.plan_routes(pol, {"agent": "claude", "model": "x", "fallback": "allow"})), 1)

    def test_grok_is_last_resort_and_gated(self):
        pol = self.cfg["policy"]
        self.assertEqual(harness.plan_routes(pol, {"agent": "claude"})[-1], ("grok", ""))
        self.assertEqual(harness.plan_routes(pol, {"agent": "grok"})[0], ("grok", ""))
        self.assertFalse(self.cfg["grok_enabled"])
        cfg = bridge.load_config(dict(ENV, BRIDGE_GROK_ENABLED="1", BRIDGE_GROK_ARGS="--foo bar"))
        self.assertEqual(bridge.build_command({"agent": "grok"}, "t", bridge.load_config(dict(ENV)))[3:], ["--permission-mode", "acceptEdits"])
        self.assertEqual(bridge.build_command({"agent": "grok"}, "t", cfg), ["grok", "-p", "t", "--foo", "bar"])
        said = []
        self.assertEqual(bridge.run_task(self.cfg, "agent: grok\nrepo: /tmp\n\nx", "g1", said.append), "rejected")

    def test_cursor_route_is_isolated_and_gated(self):
        pol = self.cfg["policy"]
        self.assertEqual(harness.plan_routes(pol, {"agent": "cursor"}), [("cursor", "")])
        self.assertFalse(self.cfg["cursor_enabled"])
        self.assertEqual(bridge.build_command({"agent": "cursor", "model": "m"}, "task",
                                              bridge.load_config(dict(ENV, BRIDGE_CURSOR_ENABLED="1"))),
                         ["cursor-agent", "-p", "task", "--output-format", "text", "--model", "m"])
        cursor_cmd = bridge.build_command({"agent": "cursor"}, "task",
                                          bridge.load_config(dict(ENV, BRIDGE_CURSOR_ENABLED="1")))
        self.assertFalse(set(cursor_cmd) & {"--force", "--yolo", "--dangerously-skip-permissions",
                                           "--dangerously-bypass-approvals-and-sandbox"})
        self.assertEqual(harness.plan_routes(pol, {"agent": "claude"})[-1], ("grok", ""))


class CursorRunTest(unittest.TestCase):
    def setup_repo(self, root):
        repo = os.path.join(root, "repo")
        os.makedirs(repo)
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
        subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        return repo

    def config(self, root, repo, binary, enabled="1"):
        return bridge.load_config(dict(ENV, BRIDGE_ALLOWED_REPOS=repo,
                                      BRIDGE_WORKTREE_DIR=os.path.join(root, "worktrees"),
                                      BRIDGE_COOLDOWN_FILE=os.path.join(root, "cooldowns.json"),
                                      BRIDGE_CURSOR_ENABLED=enabled, BRIDGE_CURSOR_BIN=binary))

    def config_with_policy(self, root, repo, binary, chains):
        policy = os.path.join(root, "routing.json")
        with open(policy, "w") as f:
            json.dump({"chains": chains}, f)
        cfg = self.config(root, repo, binary)
        cfg["policy"] = harness.load_policy(policy)
        return cfg

    def fake_cursor(self, path, exit_code=0):
        code = """#!/usr/bin/env python3
import json, os, sys
if '--help' in sys.argv:
    print('Usage: agent\\nStart the Cursor Agent\\n  -p, --print\\n  --output-format <text|json>\\n'
          '  --mode <mode>  ask: Q&A style (read-only). (choices: "plan", "ask")')
    raise SystemExit(0)
if os.environ.get('BRIDGE_TEST_CAPTURE'):
    with open(os.environ['BRIDGE_TEST_CAPTURE'], 'w') as f:
        json.dump(sys.argv[1:], f)
print('review complete')
raise SystemExit(%d)
""" % exit_code
        with open(path, "w") as f:
            f.write(code)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def test_disabled_gate_precedes_worktree_creation(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            cfg = self.config(d, repo, "/missing/cursor-agent", enabled="0")
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nreview" % repo, "disabled", said.append)
            self.assertEqual(status, "rejected")
            self.assertIn("BRIDGE_CURSOR_ENABLED=1", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_missing_binary_is_blocked_before_worktree_creation(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            cfg = self.config(d, repo, os.path.join(d, "missing"))
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nreview" % repo, "missing", said.append)
            self.assertEqual(status, "blocked (no route)")
            self.assertIn("binary not found", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_custom_cursor_chain_cannot_fall_back_to_codex(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            self.fake_cursor(binary)
            cfg = self.config_with_policy(d, repo, binary, {"cursor": ["cursor", "codex"]})
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\nfallback: allow\n\nReview." % repo,
                                     "cursor-isolated", said.append)
            self.assertEqual(status, "done")
            self.assertIn("started: cursor", said[0])
            self.assertNotIn("codex", said[-1])

    def test_non_cursor_custom_chain_cannot_reach_unverified_cursor(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "missing-cursor-agent")
            cfg = self.config_with_policy(d, repo, binary, {"claude": ["claude", "cursor"]})
            bin_dir = os.path.join(d, "bin")
            os.makedirs(bin_dir)
            claude = os.path.join(bin_dir, "claude")
            with open(claude, "w") as f:
                f.write("#!/bin/sh\necho '429 rate limit'\nexit 1\n")
            os.chmod(claude, os.stat(claude).st_mode | stat.S_IEXEC)
            old_path = os.environ["PATH"]
            os.environ["PATH"] = bin_dir + os.pathsep + old_path
            self.addCleanup(os.environ.__setitem__, "PATH", old_path)
            said = []
            status = bridge.run_task(cfg, "agent: claude\nrepo: %s\n\nReview." % repo,
                                     "cursor-filtered", said.append)
            self.assertEqual(status, "blocked (no route)")
            self.assertNotIn("cursor:", said[-1])
            self.assertNotIn("cursor-agent", said[-1])
            self.assertIn("claude unavailable (rate_limit)", said[-1])

    def test_grok_build_named_agent_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "agent")
            with open(binary, "w") as f:
                f.write("#!/bin/sh\necho 'Grok Build TUI command line options -p --output-format text'\n")
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)
            cfg = self.config(d, repo, binary)
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nreview" % repo, "grok-alias", said.append)
            self.assertEqual(status, "rejected")
            self.assertIn("did not identify itself as Cursor", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_cursor_help_without_required_options_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            with open(binary, "w") as f:
                f.write("#!/bin/sh\necho 'Cursor CLI but no supported print mode'\n")
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)
            cfg = self.config(d, repo, binary)
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nReview." % repo,
                                     "cursor-unsupported", said.append)
            self.assertEqual(status, "rejected")
            self.assertIn("does not advertise required", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_cursor_help_without_ask_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            with open(binary, "w") as f:
                f.write("#!/bin/sh\necho 'Cursor Agent -p --print --output-format text'\n")
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)
            cfg = self.config(d, repo, binary)
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nReview." % repo, "no-ask", said.append)
            self.assertEqual(status, "rejected")
            self.assertIn("--mode ask", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_cursor_run_argv_has_no_write_or_bypass_flags(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            self.fake_cursor(binary)
            capture = os.path.join(d, "argv.json")
            os.environ["BRIDGE_TEST_CAPTURE"] = capture
            self.addCleanup(os.environ.pop, "BRIDGE_TEST_CAPTURE", None)
            said = []
            status = bridge.run_task(self.config(d, repo, binary), "agent: cursor\nrepo: %s\n\nReview." % repo,
                                     "argv", said.append)
            self.assertEqual(status, "done")
            with open(capture) as f:
                argv = json.load(f)
            self.assertEqual(argv[0], "-p")
            self.assertTrue(argv[1].startswith(harness.CURSOR_PREAMBLE))
            self.assertEqual(argv[2:], ["--output-format", "text"])
            self.assertFalse(set(argv) & {"--force", "-f", "--yolo", "--sandbox", "--approve-mcps",
                                          "--auto-review", "--api-key", "--endpoint", "--worktree"})

    def test_cursor_help_failure_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            with open(binary, "w") as f:
                f.write("#!/bin/sh\necho 'Cursor CLI'\nexit 2\n")
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)
            cfg = self.config(d, repo, binary)
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nReview." % repo,
                                     "cursor-help-failed", said.append)
            self.assertEqual(status, "blocked (no route)")
            self.assertIn("--help failed", said[0])
            self.assertFalse(os.path.exists(cfg["worktrees"]))

    def test_cursor_contract_runs_read_only_command_without_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary, capture = os.path.join(d, "cursor-agent"), os.path.join(d, "args.json")
            self.fake_cursor(binary)
            cfg = self.config(d, repo, binary)
            old_capture = os.environ.get("BRIDGE_TEST_CAPTURE")
            os.environ["BRIDGE_TEST_CAPTURE"] = capture
            self.addCleanup(lambda: os.environ.pop("BRIDGE_TEST_CAPTURE", None) if old_capture is None else os.environ.__setitem__("BRIDGE_TEST_CAPTURE", old_capture))
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\nmodel: gpt-test\n\nReview source." % repo,
                                     "cursor-ok", said.append)
            self.assertEqual(status, "done")
            with open(capture) as f:
                args = json.load(f)
            self.assertEqual(args[:1], ["-p"])
            self.assertIn("--output-format", args)
            self.assertIn("text", args)
            self.assertEqual(args[-2:], ["--model", "gpt-test"])
            self.assertIn("read-only review", args[1])
            self.assertIn("Do not edit, create, delete, commit, or publish files.", args[1])
            self.assertIn("started: cursor", said[0])

    def test_cursor_task_failure_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as d:
            repo = self.setup_repo(d)
            binary = os.path.join(d, "cursor-agent")
            self.fake_cursor(binary, exit_code=1)
            cfg = self.config(d, repo, binary)
            said = []
            status = bridge.run_task(cfg, "agent: cursor\nrepo: %s\n\nReview source." % repo,
                                     "cursor-fail", said.append)
            self.assertEqual(status, "failed (exit 1)")
            self.assertIn("review complete", said[-1])
            self.assertNotIn("route:", said[-1])
            self.assertNotIn("codex", said[-1])

    def test_unavailable_kind_only_on_failure(self):
        self.assertIsNone(harness.unavailable_kind(0, "429 rate limit"))
        self.assertEqual(harness.unavailable_kind(1, "x\nusage limit, resets at 5pm")[0], "rate_limit")
        self.assertEqual(harness.unavailable_kind(1, "Not logged in")[0], "auth")
        self.assertEqual(harness.unavailable_kind(1, "Error: Not signed in. run grok login")[0], "auth")
        self.assertEqual(harness.unavailable_kind(1, "You've hit your session limit · resets 2:50pm (Asia/Tokyo)"),
                         ("rate_limit", "You've hit your session limit · resets 2:50pm (Asia/Tokyo)"))
        self.assertEqual(harness.unavailable_kind(1, "API Error 529 overloaded")[0], "model_unavailable")
        self.assertIsNone(harness.unavailable_kind(1, "assertion failed"))

    def test_cooldown_expires(self):
        now = [1000.0]
        with tempfile.TemporaryDirectory() as d:
            c = harness.Cooldowns(os.path.join(d, "c.json"), clock=lambda: now[0])
            c.mark(("claude", "m"), "rate_limit", 60)
            self.assertTrue(c.active(("claude", "m")))
            now[0] = 1061
            self.assertIsNone(c.active(("claude", "m")))


class FallbackRunTest(unittest.TestCase):
    """End-to-end run_task with fake agent binaries on PATH."""

    def fake(self, d, name, code, text):
        path = os.path.join(d, name)
        with open(path, "w") as f:
            f.write("#!/bin/sh\necho %s\nexit %d\n" % (shlex.quote(text), code))
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def run_contract(self, header, claude=(1, "You've hit your session limit · resets 2:50pm (Asia/Tokyo)")):
        d = tempfile.mkdtemp()
        repo = os.path.join(d, "repo")
        os.makedirs(repo)
        for cmd in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"]):
            subprocess.run(["git", "-C", repo] + cmd, check=True)
        bin_dir = os.path.join(d, "bin")
        os.makedirs(bin_dir)
        self.fake(bin_dir, "claude", *claude)
        self.fake(bin_dir, "codex", 0, "codex ok")
        cfg = bridge.load_config(dict(ENV, BRIDGE_ALLOWED_REPOS=repo, BRIDGE_WORKTREE_DIR=os.path.join(d, "wt"),
                                      BRIDGE_COOLDOWN_FILE=os.path.join(d, "cd.json")))
        old = os.environ["PATH"]
        os.environ["PATH"] = bin_dir + os.pathsep + old
        self.addCleanup(os.environ.__setitem__, "PATH", old)
        said = []
        status = bridge.run_task(cfg, "agent: claude\nrepo: %s\n%s\n\ndo it" % (repo, header), "t1", said.append)
        return status, said, cfg

    def test_rate_limited_claude_falls_back_visibly(self):
        status, said, cfg = self.run_contract("")
        self.assertEqual(status, "done")
        self.assertIn("route:", said[-1])
        self.assertIn("claude:claude-opus-5-5 unavailable (rate_limit)", said[-1])
        self.assertIn("ran codex:gpt-6-luna", said[-1])
        # the cooldown means a second task skips the dead routes without running them
        self.assertTrue(harness.Cooldowns(cfg["cooldowns"]).active(("claude", "claude-opus-5-5")))

    def test_pinned_model_never_falls_back(self):
        status, said, _ = self.run_contract("model: claude-opus-5-5")
        self.assertEqual(status, "blocked (no route)")
        self.assertIn("You've hit your session limit · resets 2:50pm (Asia/Tokyo)", said[-1])
        self.assertNotIn("codex", said[-1].split("```")[0].replace("fallback", ""))

    def test_real_failure_does_not_fall_back(self):
        status, said, _ = self.run_contract("", claude=(1, "AssertionError in test"))
        self.assertEqual(status, "failed (exit 1)")


if __name__ == "__main__":
    unittest.main()
