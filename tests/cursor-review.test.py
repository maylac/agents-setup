import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
HELPER = REPO / "skills/cursor-review/scripts/cursor-review"
CURSOR_HELP = 'Start the Cursor Agent\\n  -p, --print\\n  --output-format <format>\\n  --mode <mode> (choices: "plan", "ask")'


class CursorReviewHelperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name).resolve()
        self.work = self.home / "work"
        (self.home / "Downloads/pkg").mkdir(parents=True)
        self.work.mkdir()
        self.capture = self.home / "argv.json"
        self.fake = self.fake_cli(CURSOR_HELP)

    def tearDown(self):
        self.tmp.cleanup()

    def fake_cli(self, help_text, name="cursor-agent"):
        path = self.home / name
        path.write_text(
            "#!%s\nimport json, os, sys\n"
            "if sys.argv[1:] == ['--help']:\n    print('%s'); raise SystemExit(0)\n"
            "json.dump({'argv': sys.argv[1:], 'peer': os.environ.get('CROSS_HARNESS_PEER')},"
            " open(%r, 'w'))\nprint('ok')\n" % (sys.executable, help_text, str(self.capture)),
            encoding="utf-8")
        path.chmod(0o755)
        return path

    def run_helper(self, *args, cwd=None, binary=None):
        env = dict(os.environ, HOME=str(self.home), CURSOR_REVIEW_BIN=str(binary or self.fake))
        return subprocess.run([sys.executable, str(HELPER), *args], cwd=cwd or self.work,
                              capture_output=True, text=True, env=env, timeout=20)

    def captured(self):
        return json.loads(self.capture.read_text())

    def test_forces_ask_mode_and_marks_peer(self):
        proc = self.run_helper("-p", "review this", "--model", "m")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        got = self.captured()
        self.assertEqual(got["argv"][:2], ["--mode", "ask"])
        self.assertEqual(got["argv"][2:], ["-p", "review this", "--output-format", "text", "--model", "m"])
        for flag in ("--trust", "--force", "--yolo", "--sandbox", "--approve-mcps",
                     "--auto-review", "--api-key", "--endpoint", "--worktree"):
            self.assertNotIn(flag, got["argv"])
        self.assertEqual(got["peer"], "1")

    def test_redundant_ask_mode_and_json_are_accepted(self):
        proc = self.run_helper("-p", "x", "--output-format", "json", "--mode", "ask")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.captured()["argv"].count("--mode"), 1)

    def test_unsafe_or_unknown_flags_are_refused(self):
        for extra in (["--force"], ["-f"], ["--yolo"], ["--trust"], ["--sandbox", "disabled"], ["--approve-mcps"],
                      ["--mode", "plan"], ["--api-key", "k"], ["--endpoint", "u"], ["--worktree"],
                      ["--output-format", "stream-json"], ["--auto-review"]):
            proc = self.run_helper("-p", "x", *extra)
            self.assertEqual(proc.returncode, 2, extra)
            self.assertIn("refused", proc.stderr)
        self.assertFalse(self.capture.exists())

    def test_missing_prompt_is_refused(self):
        self.assertEqual(self.run_helper().returncode, 2)

    def test_non_cursor_binary_is_refused(self):
        grok = self.fake_cli("Grok Build TUI -p --output-format text --mode ask", name="agent")
        proc = self.run_helper("-p", "x", binary=grok)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("does not identify", proc.stderr)
        self.assertFalse(self.capture.exists())

    def test_cursor_without_ask_mode_is_refused(self):
        old = self.fake_cli("Start the Cursor Agent -p --output-format text", name="old-cursor")
        proc = self.run_helper("-p", "x", binary=old)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--mode ask", proc.stderr)

    def test_untrusted_working_directories_are_refused(self):
        for cwd in (self.home, self.home / "Downloads", self.home / "Downloads/pkg"):
            proc = self.run_helper("-p", "x", cwd=cwd)
            self.assertEqual(proc.returncode, 2, cwd)
        self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
