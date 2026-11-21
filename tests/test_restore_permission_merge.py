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
    def test_claude_candidate_is_narrow_idempotent_and_redacted(self):
        source = python_block('python3 - "$HOME/.claude/settings.json"')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            live, candidate, second = root / "settings.json", root / "candidate.json", root / "candidate-2.json"
            fixture = {
                "hooks": {"PostToolUse": [{"command": "preserve-hook"}]},
                "opaque_secret": "fixture-secret-must-not-print",
                "nas_profile": {"alias": "fixture-nas", "command": "ssh fixture-nas"},
                "gh_profile": {"host": "github.example.invalid", "extension": "preserve-gh"},
                "permissions": {
                    "defaultMode": "auto",
                    "allow": ["Bash", "Bash(launchctl:*)", "Bash(gh api:*)"],
                    "ask": ["Bash(codex exec:*)", "Bash(custom ask:*)"],
                    "deny": [
                        "Bash(custom deny:*)", "Bash(launchctl bootout:*)", "Bash(launchctl kickstart:*)",
                        "Bash(launchctl unload:*)", "Bash(gh pr merge:*)", "Bash(gh auth:*)",
                    ],
                    "custom": True,
                },
                "sandbox": {
                    "enabled": True,
                    "autoAllowBashIfSandboxed": True,
                    "allowUnsandboxedCommands": False,
                    "excludedCommands": ["gh *", "codex *"],
                    "network": {"allowedDomains": ["fixture.invalid"], "allowLocalBinding": True},
                    "filesystem": {
                        "allowWrite": ["~/tasks"],
                        "denyWrite": ["~/.claude"],
                        "denyRead": ["~/.ssh"],
                        "opaque": "fixture-sandbox-value",
                    },
                    "opaque": {"retained": "fixture-sandbox-opaque"},
                },
            }
            original = json.dumps(fixture, indent=2)
            live.write_text(original)
            template = ROOT / "templates/claude-settings.permissions.json"
            proposed = json.loads(template.read_text())
            self.assertEqual(set(proposed["permissions"]), {"allow", "ask", "deny"})
            self.assertEqual(proposed["permissions"]["allow"], ["Bash(launchctl print:*)", "Bash(launchctl list:*)"])
            self.assertEqual(proposed["permissions"]["ask"], [
                "Bash(launchctl bootstrap:*)", "Bash(launchctl bootout:*)", "Bash(launchctl kickstart:*)",
                "Bash(launchctl load:*)", "Bash(launchctl unload:*)", "Bash(launchctl enable:*)",
                "Bash(launchctl disable:*)", "Bash(gh pr merge:*)", "Bash(gh auth:*)",
            ])
            self.assertEqual(proposed["permissions"]["deny"], [
                "Bash(git push *--force*)", "Bash(git push *-f *)", "Bash(git push *+*)",
                "Bash(gh repo delete:*)", "Bash(gh issue delete:*)", "Bash(gh secret:*)",
                "Bash(gh auth token:*)", "Bash(codex *--dangerously*)", "Read(~/.config/gh/**)",
                "Read(~/.config/slack-bridge/**)", "Read(~/.codex/auth.json)",
                "Read(~/.claude/.credentials.json)",
            ])
            self.assertNotIn("Read(~/.ssh/**)", proposed["permissions"]["deny"])
            self.assertNotIn("Read(~/.config/vantik/**)", proposed["permissions"]["deny"])
            self.assertEqual(proposed["sandbox"]["filesystem"]["denyRead"], ["~/.config/gh", "~/.config/slack-bridge"])
            self.assertEqual(set(proposed["sandbox"]), {"filesystem"})
            result = subprocess.run(
                [sys.executable, "-c", source, str(live), str(template), str(candidate)],
                text=True, capture_output=True, check=True,
            )
            merged = json.loads(candidate.read_text())
            self.assertNotIn("Bash", merged["permissions"]["allow"])
            self.assertNotIn("Bash(launchctl:*)", merged["permissions"]["allow"])
            self.assertIn("Bash(gh api:*)", merged["permissions"]["allow"])
            self.assertIn("Bash(codex exec:*)", merged["permissions"]["ask"])
            self.assertIn("Bash(custom ask:*)", merged["permissions"]["ask"])
            self.assertIn("Bash(custom deny:*)", merged["permissions"]["deny"])
            for operation in (
                "Bash(launchctl bootout:*)", "Bash(launchctl kickstart:*)", "Bash(launchctl unload:*)",
                "Bash(gh pr merge:*)", "Bash(gh auth:*)",
            ):
                self.assertIn(operation, merged["permissions"]["deny"])
            for operation in ("Bash(git push *--force*)", "Bash(gh repo delete:*)", "Bash(gh auth token:*)"):
                self.assertIn(operation, merged["permissions"]["deny"])
            self.assertEqual(merged["permissions"]["defaultMode"], "auto")
            self.assertEqual(merged["nas_profile"], fixture["nas_profile"])
            self.assertEqual(merged["gh_profile"], fixture["gh_profile"])
            self.assertEqual(merged["sandbox"]["enabled"], fixture["sandbox"]["enabled"])
            self.assertEqual(merged["sandbox"]["autoAllowBashIfSandboxed"], fixture["sandbox"]["autoAllowBashIfSandboxed"])
            self.assertEqual(merged["sandbox"]["allowUnsandboxedCommands"], fixture["sandbox"]["allowUnsandboxedCommands"])
            self.assertEqual(merged["sandbox"]["excludedCommands"], fixture["sandbox"]["excludedCommands"])
            self.assertEqual(merged["sandbox"]["network"], fixture["sandbox"]["network"])
            self.assertEqual(merged["sandbox"]["filesystem"]["allowWrite"], fixture["sandbox"]["filesystem"]["allowWrite"])
            self.assertEqual(merged["sandbox"]["filesystem"]["denyWrite"], fixture["sandbox"]["filesystem"]["denyWrite"])
            self.assertEqual(merged["sandbox"]["filesystem"]["opaque"], "fixture-sandbox-value")
            self.assertEqual(merged["sandbox"]["opaque"], fixture["sandbox"]["opaque"])
            self.assertEqual(merged["sandbox"]["filesystem"]["denyRead"], ["~/.ssh", "~/.config/gh", "~/.config/slack-bridge"])
            self.assertEqual(merged["hooks"], {"PostToolUse": [{"command": "preserve-hook"}]})
            self.assertEqual(merged["opaque_secret"], fixture["opaque_secret"])
            self.assertEqual(live.read_text(), original)
            self.assertEqual(candidate.stat().st_mode & 0o777, 0o600)
            self.assertEqual(result.stdout.splitlines(), [
                "permissions.allow", "permissions.ask", "permissions.deny", "sandbox.filesystem.denyRead",
            ])
            self.assertEqual(result.stderr, "")
            self.assertNotIn("fixture-secret-must-not-print", result.stdout + result.stderr)

            repeated = subprocess.run(
                [sys.executable, "-c", source, str(candidate), str(template), str(second)],
                text=True, capture_output=True, check=True,
            )
            self.assertEqual(json.loads(second.read_text()), merged)
            self.assertEqual(repeated.stdout, "")
            self.assertEqual(repeated.stderr, "")
            self.assertEqual(second.stat().st_mode & 0o777, 0o600)

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
