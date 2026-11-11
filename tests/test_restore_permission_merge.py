from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESTORE = (ROOT / "docs/restore.md").read_text(encoding="utf-8")


def python_block(marker):
    start = RESTORE.index(marker)
    start = RESTORE.index("<<'PYTHON'\n", start) + len("<<'PYTHON'\n")
    end = RESTORE.index("\nPYTHON", start)
    return RESTORE[start:end]


class RestoreCandidateFixtureTest(unittest.TestCase):
    def test_claude_merge_removes_blanket_launchctl_and_preserves_unrelated_values(self):
        source = python_block('python3 - "$HOME/.claude/settings.json"')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            live, candidate = root / "settings.json", root / "candidate.json"
            live.write_text(json.dumps({
                "hooks": {"PostToolUse": [{"command": "preserve-hook"}]},
                "opaque_secret": "fixture-secret-must-not-print",
                "permissions": {"allow": ["Bash(launchctl:*)", "Bash(custom:*)"], "custom": True, "private_extension": "fixture-secret-must-not-print"},
                "sandbox": {"custom": "fixture-secret-must-not-print", "filesystem": {"allowWrite": ["/extra"]}},
            }))
            result = subprocess.run(
                [sys.executable, "-c", source, str(live), str(ROOT / "templates/claude-settings.permissions.json"), str(candidate)],
                text=True, capture_output=True, check=True,
            )
            merged = json.loads(candidate.read_text())
            self.assertNotIn("Bash(launchctl:*)", merged["permissions"]["allow"])
            self.assertIn("Bash(custom:*)", merged["permissions"]["allow"])
            self.assertEqual(merged["permissions"]["custom"], True)
            self.assertEqual(merged["permissions"]["private_extension"], "fixture-secret-must-not-print")
            self.assertEqual(merged["sandbox"]["custom"], "fixture-secret-must-not-print")
            self.assertEqual(merged["sandbox"]["filesystem"]["allowWrite"][0], "/extra")
            self.assertEqual(merged["hooks"], {"PostToolUse": [{"command": "preserve-hook"}]})
            self.assertEqual(merged["opaque_secret"], "fixture-secret-must-not-print")
            self.assertNotIn("fixture-secret-must-not-print", result.stdout + result.stderr)

    def test_codex_validator_accepts_multiline_toml_and_redacts_unrelated_values(self):
        if not shutil.which("python3.12"):
            self.skipTest("python3.12 with tomllib is unavailable")
        source = python_block('python3.12 - "$HOME/.codex/config.toml.candidate"')
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate.toml"
            candidate.write_text('''approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n\n[mcp_servers.private]\ntoken = "fixture-secret-must-not-print"\n\n[sandbox_workspace_write]\nnetwork_access = true\nwritable_roots = [\n  "/fixture/home/tasks",\n  "/fixture/home/.local/state/slack-bridge",\n]\n\n[other]\nvalue = 1''')
            result = subprocess.run(["python3.12", "-c", source, str(candidate)], text=True, capture_output=True, check=True)
            self.assertIn("writable_roots", result.stdout)
            self.assertNotIn("fixture-secret-must-not-print", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
