import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import doctor


class DoctorTests(unittest.TestCase):
    def run_doctor(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = doctor.main(list(args))
        return code, json.loads(output.getvalue())

    def by_name(self, result, name):
        return [item for item in result["checks"] if item["name"] == name]

    def test_absent_config_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            code, result = self.run_doctor("--env-file", str(Path(directory) / "absent"))
        self.assertEqual(code, 1)
        self.assertEqual(self.by_name(result, "env_file")[0]["state"], "missing")
        self.assertEqual(self.by_name(result, "end_to_end")[0]["state"], "unknown")

    def test_env_shell_substitution_is_never_executed_and_secrets_not_printed(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=$(touch %s)\nBRIDGE_GITHUB_REPO=org/private\n"
                                "SLACK_BOT_TOKEN=top-secret\n" % marker, encoding="utf-8")
            code, result = self.run_doctor("--env-file", str(env_file))
            self.assertFalse(marker.exists())
        self.assertEqual(code, 1)
        self.assertNotIn("top-secret", json.dumps(result))
        self.assertEqual(self.by_name(result, "config:BRIDGE_GITHUB_REPO")[0]["state"], "present")

    def test_grok_agent_help_does_not_confirm_cursor_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "agent"
            binary.write_text("#!/bin/sh\nprintf 'Grok Build TUI\\n'\n", encoding="utf-8")
            binary.chmod(0o755)
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=%s\nBRIDGE_GITHUB_REPO=org/tasks\n"
                                "BRIDGE_CURSOR_BIN=%s\nBRIDGE_CURSOR_ENABLED=1\n" % (directory, binary),
                                encoding="utf-8")
            with mock.patch.dict(os.environ, {"PATH": directory}):
                _, result = self.run_doctor("--env-file", str(env_file))
        self.assertEqual(self.by_name(result, "cursor_identity")[0]["state"], "unknown")

    def test_github_check_can_report_present_or_unknown_without_response_data(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=%s\nBRIDGE_GITHUB_REPO=org/tasks\n" % directory,
                                encoding="utf-8")
            fake_gh = Path(directory) / "gh"
            fake_gh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_gh.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": directory}):
                code, result = self.run_doctor("--env-file", str(env_file), "--check-github")
            self.assertEqual(self.by_name(result, "github_repo")[0]["state"], "present")
            with mock.patch("doctor.shutil.which", return_value=None):
                _, unknown = self.run_doctor("--env-file", str(env_file), "--check-github")
        self.assertEqual(self.by_name(result, "github_repo")[0]["state"], "present")
        self.assertEqual(self.by_name(unknown, "github_repo")[0]["state"], "missing")

    def test_disabled_optional_clis_do_not_fail_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=%s\nBRIDGE_GITHUB_REPO=org/tasks\n" % directory,
                                encoding="utf-8")
            for name in ("claude", "codex"):
                binary = Path(directory) / name
                binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                binary.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": directory}), \
                    mock.patch("doctor.sys_platform_is_macos", return_value=True), \
                    mock.patch("doctor.subprocess.run", return_value=mock.Mock(returncode=0)):
                code, result = self.run_doctor("--env-file", str(env_file))
        self.assertEqual(code, 0)
        self.assertEqual(self.by_name(result, "cli:agy")[0]["state"], "missing")
        self.assertEqual(self.by_name(result, "cli:grok")[0]["state"], "disabled")
        self.assertEqual(self.by_name(result, "cli:cursor")[0]["state"], "disabled")

    def test_enabled_cursor_and_grok_missing_binaries_fail_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=%s\nBRIDGE_GITHUB_REPO=org/tasks\n"
                                "BRIDGE_CURSOR_ENABLED=1\nBRIDGE_GROK_ENABLED=1\n"
                                "BRIDGE_CURSOR_BIN=%s/no-cursor\nBRIDGE_GROK_BIN=%s/no-grok\n"
                                % (directory, directory, directory), encoding="utf-8")
            with mock.patch("doctor.shutil.which", return_value=None):
                code, result = self.run_doctor("--env-file", str(env_file))
        self.assertEqual(code, 1)
        self.assertEqual(self.by_name(result, "cli:cursor")[0]["state"], "missing")
        self.assertEqual(self.by_name(result, "cli:grok")[0]["state"], "missing")

    def test_github_auth_and_login_report_only_safe_status(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "env"
            env_file.write_text("BRIDGE_TRANSPORT=github\nBRIDGE_ALLOWED_SENDERS=org\n"
                                "BRIDGE_ALLOWED_REPOS=%s\nBRIDGE_GITHUB_REPO=org/tasks\n" % directory,
                                encoding="utf-8")
            fake_gh = Path(directory) / "gh"
            fake_gh.write_text("#!/bin/sh\ncase \"$1 $2\" in\n  'api user') echo bridge-bot;;\n  'auth status') echo TOKEN-SECRET >&2; exit 0;;\nesac\n", encoding="utf-8")
            fake_gh.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": directory}), mock.patch("doctor.sys_platform_is_macos", return_value=False):
                code, result = self.run_doctor("--env-file", str(env_file))
        self.assertEqual(self.by_name(result, "github_auth")[0]["state"], "present")
        self.assertEqual(self.by_name(result, "github_login")[0]["state"], "present")
        self.assertNotIn("TOKEN-SECRET", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
