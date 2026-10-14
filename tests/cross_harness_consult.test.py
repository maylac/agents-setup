import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
HELPER = REPO / "skills/cross-harness-collab/scripts/consult.py"


FAKE_CLI = r'''#!{python}
import json, os, signal, sys, time
import shutil
name = os.path.basename(sys.argv[0])
if os.environ.get("FAKE_CHECK_SIBLING") and not shutil.which("codex-code-mode-host"):
    print("missing sibling executable", file=sys.stderr)
    sys.exit(9)
if os.environ.get("FAKE_RECORD"):
    with open(os.environ["FAKE_RECORD"], "w") as f:
        json.dump({"executable": sys.argv[0], "argv": sys.argv[1:], "stdin": sys.stdin.read(),
                   "peer": os.environ.get("CROSS_HARNESS_PEER"),
                   "worker": os.environ.get("CROSS_HARNESS_WORKER"),
                   "sibling": shutil.which("codex-code-mode-host")}, f)
mode = os.environ.get("FAKE_MODE", "success")
if mode == "timeout":
    child = os.fork()
    if child == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if os.environ.get("FAKE_CLOSED_PIPES"):
            os.close(1)
            os.close(2)
        while True: time.sleep(1)
    with open(os.environ["FAKE_CHILD_PID"], "w") as f: f.write(str(child))
    while True: time.sleep(1)
if mode == "nonzero":
    print("simulated CLI failure", file=sys.stderr)
    sys.exit(7)
if mode == "malformed":
    print("not json")
    sys.exit(0)
if mode == "empty":
    print("{}")
    sys.exit(0)
if mode == "claude_error":
    print(json.dumps({"type": "result", "subtype": "error_api", "is_error": True,
                      "result": "simulated model error"}))
    sys.exit(0)
if mode == "claude_mismatch":
    print(json.dumps({"type": "result", "subtype": "success", "session_id": "s-2",
                      "result": "Mismatch response", "modelUsage": {
                          "claude-sonnet-5": {"canonicalModel": "claude-sonnet-5"}}}))
    sys.exit(0)
if mode == "claude_ambiguous":
    print(json.dumps({"type": "result", "subtype": "success", "result": "Ambiguous response",
                      "modelUsage": {"claude-opus-5-5": {}, "claude-sonnet-5": {}}}))
    sys.exit(0)
if name == "claude":
    print(json.dumps({"type": "result", "subtype": "success", "session_id": "s-1",
                      "result": "Claude peer result", "modelUsage": {
                          "claude-opus-5-5": {"canonicalModel": "claude-opus-5-5",
                                               "inputTokens": 8}}}))
else:
    print(json.dumps({"type": "thread.started", "thread_id": "t-1"}))
    print(json.dumps({"type": "item.completed", "item": {
        "type": "agent_message", "phase": "commentary", "text": "Intermediate note"}}))
    print(json.dumps({"type": "item.completed", "item": {
        "type": "agent_message", "phase": "final_answer", "text": "Codex peer result"}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 4}}))
'''.replace("{python}", sys.executable)


class ConsultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("claude", "codex"):
            path = self.bin / name
            path.write_text(FAKE_CLI)
            path.chmod(0o755)
        self.cwd = self.root / "repo"
        self.cwd.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, target="claude", brief="Review the scoped change", mode="success",
               extra=(), timeout=5, extra_env=None, helper_mode=None, owned=()):
        env = {"PATH": f"{self.bin}:{os.environ.get('PATH', '')}", "FAKE_MODE": mode}
        if extra_env:
            env.update(extra_env)
        args = [sys.executable, str(HELPER), "--target", target, "--cwd", str(self.cwd)]
        if helper_mode is not None:
            args.extend(("--mode", helper_mode))
        for path in owned:
            args.extend(("--owned-path", path))
        if timeout is not None:
            timeout_arg = str(timeout)
            args.append(f"--timeout={timeout_arg}" if timeout_arg.startswith("-")
                        else "--timeout")
            if not timeout_arg.startswith("-"):
                args.append(timeout_arg)
        args.extend(extra)
        result = subprocess.run(
            args,
            input=brief, text=True, capture_output=True, env=env, timeout=8,
        )
        receipt = json.loads(result.stdout) if result.stdout else None
        return result, receipt

    def test_claude_dispatch_and_observed_metadata(self):
        record = self.root / "record.json"
        result, receipt = self.invoke(extra_env={"FAKE_RECORD": str(record)})
        sent = json.loads(record.read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["mode"], "consult")
        self.assertEqual(receipt["timeout_seconds"], 5)
        self.assertEqual(receipt["owned_paths"], [])
        self.assertEqual(receipt["requested_model"], "claude-opus-5-5")
        self.assertEqual(receipt["observed_model"], "claude-opus-5-5")
        self.assertEqual(receipt["observed_models"], ["claude-opus-5-5"])
        self.assertTrue(receipt["model_verified"])
        self.assertEqual(receipt["session_id"], "s-1")
        self.assertEqual(receipt["result"], "Claude peer result")
        self.assertIn("--permission-mode", sent["argv"])
        self.assertIn("dontAsk", sent["argv"])
        self.assertNotIn("plan", sent["argv"])
        self.assertIn("--setting-sources", sent["argv"])
        settings_index = sent["argv"].index("--setting-sources")
        self.assertEqual(sent["argv"][settings_index + 1], "")
        self.assertTrue(sent["stdin"].startswith("You are a delegated peer"))
        self.assertNotIn("BRIEF", sent["argv"])
        self.assertIn("--strict-mcp-config", sent["argv"])
        mcp_index = sent["argv"].index("--mcp-config")
        self.assertEqual(sent["argv"][mcp_index + 1], '{"mcpServers":{}}')
        self.assertIn("--max-budget-usd", sent["argv"])
        self.assertEqual(sent["peer"], "1")
        self.assertIn("Do not edit files", sent["stdin"])

    def test_codex_dispatch_uses_stdin_and_does_not_infer_model(self):
        record = self.root / "record.json"
        result, receipt = self.invoke("codex", extra=("--model", "requested-model",
                                                       "--effort", "high"),
                                      extra_env={"FAKE_RECORD": str(record)})
        sent = json.loads(record.read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["requested_model"], "requested-model")
        self.assertIsNone(receipt["observed_model"])
        self.assertEqual(receipt["thread_id"], "t-1")
        self.assertEqual(receipt["usage"], {"input_tokens": 4})
        self.assertEqual(receipt["result"], "Codex peer result")
        self.assertTrue(sent["stdin"].splitlines()[0].startswith("You are a delegated peer"))
        self.assertEqual(sent["peer"], "1")
        self.assertIn("--sandbox", sent["argv"])
        self.assertIn("read-only", sent["argv"])
        self.assertIn("model_reasoning_effort=high", sent["argv"])
        self.assertIn("project_doc_max_bytes=0", sent["argv"])
        self.assertIn("hooks", sent["argv"])
        self.assertIn("--ephemeral", sent["argv"])
        self.assertIn("--skip-git-repo-check", sent["argv"])
        self.assertFalse(receipt["model_verified"])

    def test_rejects_empty_brief_and_nested_consult(self):
        result, receipt = self.invoke(brief="  ")
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty", receipt["error"])
        result, receipt = self.invoke(extra_env={"CROSS_HARNESS_PEER": "1"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("nested", receipt["error"])
        result, receipt = self.invoke(extra_env={"CROSS_HARNESS_WORKER": "1"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("nested", receipt["error"])

    def test_rejects_nonfinite_and_nonpositive_timeouts(self):
        for timeout in (0, "NaN", "Inf", "-Inf"):
            with self.subTest(timeout=timeout):
                result, receipt = self.invoke(timeout=timeout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("finite and positive", receipt["error"])
                if str(timeout).lower() in {"nan", "inf", "-inf"}:
                    self.assertIsNone(receipt["timeout_seconds"])
        result, receipt = self.invoke(extra_env={"CROSS_HARNESS_WORKER": "1"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("nested", receipt["error"])

    def test_rejects_cli_and_structured_response_failures(self):
        for mode, phrase in (("nonzero", "exited 7"), ("malformed", "malformed JSON"),
                             ("empty", "empty result"), ("claude_error", "simulated model error")):
            with self.subTest(mode=mode):
                result, receipt = self.invoke(mode=mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(receipt["status"], "error")
                self.assertIn(phrase, receipt["error"])

    def test_pinned_model_mismatch_fails_and_aliases_are_not_rejected(self):
        result, receipt = self.invoke(extra=("--model", "claude-opus-5-5"), mode="claude_mismatch")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match", receipt["error"])
        self.assertEqual(receipt["observed_models"], ["claude-sonnet-5"])
        result, receipt = self.invoke(extra=("--model", "opus"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["observed_model"], "claude-opus-5-5")
        self.assertFalse(receipt["model_verified"])
        result, receipt = self.invoke(mode="claude_ambiguous")
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(receipt["observed_model"])
        self.assertEqual(set(receipt["observed_models"]), {"claude-opus-5-5", "claude-sonnet-5"})
        self.assertFalse(receipt["model_verified"])

    def test_work_mode_claude_has_owned_paths_and_scoped_write_tools(self):
        record = self.root / "work-claude.json"
        result, receipt = self.invoke(helper_mode="work", timeout=None,
                                      owned=("src/new.py", "docs"),
                                      extra_env={"FAKE_RECORD": str(record)})
        sent = json.loads(record.read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["mode"], "work")
        self.assertEqual(receipt["requested_model"], "claude-opus-5-5")
        self.assertEqual(receipt["effort"], "medium")
        self.assertEqual(receipt["status"], "returned")
        self.assertFalse(receipt["task_verified"])
        self.assertIn("inspect the owned paths", receipt["owner_action"])
        self.assertEqual(receipt["timeout_seconds"], 600)
        self.assertEqual(receipt["owned_paths"], ["src/new.py", "docs"])
        self.assertEqual(sent["worker"], "1")
        self.assertIsNone(sent["peer"])
        self.assertIn("CROSS_HARNESS_WORKER=1", sent["stdin"])
        self.assertIn("instruction-level contract", sent["stdin"])
        self.assertIn("- src/new.py", sent["stdin"])
        self.assertIn("- docs", sent["stdin"])
        argv = sent["argv"]
        self.assertIn("acceptEdits", argv)
        self.assertIn("--safe-mode", argv)
        self.assertIn("--strict-mcp-config", argv)
        self.assertIn("--no-session-persistence", argv)
        self.assertIn("--max-budget-usd", argv)
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "5.00")
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep,Edit,Write,Bash")

    def test_work_mode_codex_defaults_and_write_sandbox(self):
        record = self.root / "work-codex.json"
        result, receipt = self.invoke("codex", helper_mode="work", timeout=None,
                                      owned=("notes.md",),
                                      extra_env={"FAKE_RECORD": str(record)})
        sent = json.loads(record.read_text())
        argv = sent["argv"]
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["requested_model"], "gpt-6-luna")
        self.assertEqual(receipt["effort"], "high")
        self.assertEqual(receipt["status"], "returned")
        self.assertFalse(receipt["task_verified"])
        self.assertIn("acceptance checks", receipt["owner_action"])
        self.assertEqual(receipt["timeout_seconds"], 600)
        self.assertEqual(receipt["owned_paths"], ["notes.md"])
        self.assertEqual(sent["worker"], "1")
        self.assertIn("workspace-write", argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--ignore-rules", argv)
        self.assertIn("--disable", argv)
        self.assertIn("hooks", argv)
        self.assertIn("--skip-git-repo-check", argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
        result, receipt = self.invoke("codex", helper_mode="work", timeout=None,
                                      owned=("notes.md",),
                                      extra=("--model", "codex-alias", "--effort", "medium"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["requested_model"], "codex-alias")
        self.assertEqual(receipt["effort"], "medium")

    def test_codex_symlinked_cli_can_find_bundle_sibling(self):
        bundle = self.root / "codex-bundle"
        link_dir = self.root / "launcher"
        bundle.mkdir()
        link_dir.mkdir()
        real_cli = bundle / "codex"
        real_cli.write_text(FAKE_CLI)
        real_cli.chmod(0o755)
        helper = bundle / "codex-code-mode-host"
        helper.write_text("#!/bin/sh\nexit 0\n")
        helper.chmod(0o755)
        (link_dir / "codex").symlink_to(real_cli)
        record = self.root / "symlinked-codex.json"
        env = {"PATH": f"{link_dir}{os.pathsep}{os.environ.get('PATH', '')}",
               "FAKE_RECORD": str(record), "FAKE_CHECK_SIBLING": "1"}
        result, receipt = self.invoke("codex", helper_mode="work", timeout=None,
                                      owned=("scratch.txt",), extra_env=env)
        sent = json.loads(record.read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(receipt["status"], "returned")
        self.assertEqual(pathlib.Path(sent["sibling"]).resolve(), helper.resolve())
        self.assertEqual(sent["executable"], str(real_cli.resolve()))

    def test_work_mode_rejects_missing_and_escaping_ownership(self):
        result, receipt = self.invoke(helper_mode="work")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires at least one", receipt["error"])
        self.assertFalse(receipt["partial_changes_possible"])
        self.assertIn("correct the work request", receipt["owner_action"])
        result, receipt = self.invoke(helper_mode="work", owned=("  ",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not be empty", receipt["error"])
        self.assertFalse(receipt["partial_changes_possible"])
        for path, phrase in (("../outside.txt", "escapes --cwd"),
                             (str(self.root / "absolute.txt"), "relative to --cwd")):
            with self.subTest(path=path):
                result, receipt = self.invoke(helper_mode="work", owned=(path,))
                self.assertEqual(result.returncode, 1)
                self.assertIn(phrase, receipt["error"])
                self.assertFalse(receipt["partial_changes_possible"])
        outside = self.root / "outside"
        outside.mkdir()
        (self.cwd / "escape").symlink_to(outside, target_is_directory=True)
        result, receipt = self.invoke(helper_mode="work", owned=("escape/secret.md",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("escapes --cwd", receipt["error"])

    def test_work_failure_warns_owner_to_inspect_before_retry(self):
        result, receipt = self.invoke(mode="nonzero", helper_mode="work", owned=("file.md",))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(receipt["partial_changes_possible"])
        self.assertIn("inspect the owned paths", receipt["owner_action"])

    def test_timeout_kills_the_whole_process_group(self):
        pid_file = self.root / "child.pid"
        result, receipt = self.invoke(mode="timeout", timeout=0.2,
                                     extra_env={"FAKE_CHILD_PID": str(pid_file)})
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", receipt["error"])
        child = int(pid_file.read_text())
        self.assert_process_inactive(child)

    def assert_process_inactive(self, child):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            status = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(child)],
                                    text=True, capture_output=True).stdout.strip()
            if not status or status.startswith("Z"):
                break
            time.sleep(0.05)
        else:
            self.fail("timed-out child process survived group cleanup")

    def test_timeout_kills_grandchild_even_if_it_closed_output_pipes(self):
        pid_file = self.root / "closed-pipe-child.pid"
        result, receipt = self.invoke(mode="timeout", timeout=0.2,
                                     extra_env={"FAKE_CHILD_PID": str(pid_file),
                                                "FAKE_CLOSED_PIPES": "1"})
        self.assertEqual(result.returncode, 124)
        self.assert_process_inactive(int(pid_file.read_text()))

    def test_signal_reaps_peer_process_group(self):
        pid_file = self.root / "signal-child.pid"
        env = os.environ.copy()
        env.update({"PATH": f"{self.bin}:{os.environ.get('PATH', '')}",
                    "FAKE_MODE": "timeout", "FAKE_CHILD_PID": str(pid_file),
                    "FAKE_CLOSED_PIPES": "1"})
        proc = subprocess.Popen([sys.executable, str(HELPER), "--target", "claude",
                                 "--cwd", str(self.cwd), "--timeout", "10"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=env)
        proc.stdin.write("Review this change")
        proc.stdin.close()
        proc.stdin = None
        deadline = time.monotonic() + 3
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(pid_file.exists(), "fake peer did not start")
        child = int(pid_file.read_text())
        proc.send_signal(signal.SIGTERM)
        stdout, _ = proc.communicate(timeout=4)
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
        self.assertEqual(json.loads(stdout)["status"], "error")
        self.assert_process_inactive(child)


if __name__ == "__main__":
    unittest.main()
