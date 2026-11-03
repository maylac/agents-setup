from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "team_gate.py"
sys.path.insert(0, str(SCRIPT.parent))
import team_gate


class TeamGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "Gate Test")
        (self.root / "owned.txt").write_text("base\n", encoding="utf-8")
        self.run_git("add", "owned.txt")
        self.run_git("commit", "-qm", "base")
        self.base = self.run_git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def cli(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                              input=input_text, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

    def init(self, session: str, *checks: str) -> subprocess.CompletedProcess[str]:
        args = ["init", "--session", session, "--cwd", str(self.root),
                "--base-sha", self.base, "--owned-path", "owned.txt"]
        for check in checks or ("true",):
            args.extend(("--check", check))
        return self.cli(*args)

    def hook_stop(self, session: str) -> subprocess.CompletedProcess[str]:
        return self.cli("hook-stop", input_text=json.dumps({
            "session_id": session, "cwd": str(self.root), "stop_hook_active": False,
        }))

    def test_ready_requires_passed_checks_and_snapshot_bound_review(self) -> None:
        self.assertEqual(self.init("ready1").returncode, 0)
        (self.root / "owned.txt").write_text("updated\n", encoding="utf-8")
        state_path = next((self.root / ".git" / "team-runs" / "autonomous-team").glob("ready1-*.json"))
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["stop_blocks"] = 2
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.cli("check", "--session", "ready1", "--cwd", str(self.root)).returncode, 0)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["stop_blocks"], 0)
        snapshot_result = self.cli("snapshot", "--session", "ready1", "--cwd", str(self.root))
        self.assertEqual(snapshot_result.returncode, 0, snapshot_result.stderr)
        snapshot = snapshot_result.stdout.strip().removeprefix("Snapshot: ")
        evidence = Path(self.temp.name) / "review.md"
        evidence.write_text(f"Reviewed integrated diff; no findings.\nSnapshot: {snapshot}\n", encoding="utf-8")
        state["stop_blocks"] = 2
        state_path.write_text(json.dumps(state), encoding="utf-8")
        reviewed = self.cli("review", "--session", "ready1", "--cwd", str(self.root),
                            "--outcome", "pass", "--evidence", str(evidence), "--snapshot", snapshot)
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["stop_blocks"], 0)
        self.assertEqual(self.cli("finish", "--session", "ready1", "--cwd", str(self.root),
                                  "--outcome", "ready").returncode, 0)
        self.assertEqual(self.hook_stop("ready1").stdout, "")

        (self.root / "owned.txt").write_text("changed after review\n", encoding="utf-8")
        stale = self.cli("finish", "--session", "ready1", "--cwd", str(self.root), "--outcome", "ready")
        self.assertEqual(stale.returncode, 2)
        gate = self.hook_stop("ready1")
        self.assertEqual(json.loads(gate.stdout)["decision"], "block")

    def test_check_failure_and_out_of_scope_untracked_file_are_rejected(self) -> None:
        self.assertEqual(self.init("fail1", "true", "echo useful-error >&2; false").returncode, 0)
        (self.root / "owned.txt").write_text("changed\n", encoding="utf-8")
        failed = self.cli("check", "--session", "fail1", "--cwd", str(self.root))
        self.assertEqual(failed.returncode, 2)
        self.assertIn("acceptance checks failed", failed.stderr)
        self.assertIn("useful-error", failed.stdout)
        self.assertEqual(len(list((self.root / ".git" / "team-runs" / "autonomous-team").glob("fail1-*.checks.log"))), 1)

        self.run_git("restore", "owned.txt")
        self.assertEqual(self.init("scope1").returncode, 0)
        (self.root / "owned.txt").write_text("changed\n", encoding="utf-8")
        (self.root / "outside.txt").write_text("new\n", encoding="utf-8")
        scoped = self.cli("check", "--session", "scope1", "--cwd", str(self.root))
        self.assertEqual(scoped.returncode, 2)
        self.assertIn("outside.txt", scoped.stderr)

    def test_rename_keeps_out_of_scope_deletion_visible(self) -> None:
        (self.root / "outside.txt").write_text("old\n", encoding="utf-8")
        self.run_git("add", "outside.txt")
        self.run_git("commit", "-qm", "add outside file")
        self.base = self.run_git("rev-parse", "HEAD").stdout.strip()
        init = self.cli("init", "--session", "rename1", "--cwd", str(self.root),
                        "--base-sha", self.base, "--owned-path", "owned/", "--check", "true")
        self.assertEqual(init.returncode, 0, init.stderr)
        destination = self.root / "owned"
        destination.mkdir()
        self.run_git("mv", "outside.txt", "owned/new.txt")
        check = self.cli("check", "--session", "rename1", "--cwd", str(self.root))
        self.assertEqual(check.returncode, 2)
        self.assertIn("outside.txt", check.stderr)

    def test_preexisting_unowned_change_is_preserved_but_new_one_is_blocked(self) -> None:
        (self.root / "personal.txt").write_text("keep\n", encoding="utf-8")
        self.assertEqual(self.init("base1").returncode, 0)
        (self.root / "owned.txt").write_text("task change\n", encoding="utf-8")
        self.assertEqual(self.cli("check", "--session", "base1", "--cwd", str(self.root)).returncode, 0)
        (self.root / "personal.txt").write_text("modified during task\n", encoding="utf-8")
        scoped = self.cli("check", "--session", "base1", "--cwd", str(self.root))
        self.assertEqual(scoped.returncode, 2)
        self.assertIn("personal.txt", scoped.stderr)
        (self.root / "personal.txt").unlink()
        restored = self.cli("check", "--session", "base1", "--cwd", str(self.root))
        self.assertEqual(restored.returncode, 2)
        self.assertIn("personal.txt", restored.stderr)

    def test_sessions_are_separate_and_corrupt_state_blocks_once(self) -> None:
        self.assertEqual(self.init("one").returncode, 0)
        self.assertEqual(self.init("two").returncode, 0)
        state_dir = self.root / ".git" / "team-runs" / "autonomous-team"
        one = next(state_dir.glob("one-*.json"))
        two = next(state_dir.glob("two-*.json"))
        self.assertNotEqual(one, two)
        one.write_text("{bad", encoding="utf-8")
        first = json.loads(self.hook_stop("one").stdout)
        second = json.loads(self.hook_stop("one").stdout)
        self.assertEqual(first["decision"], "block")
        self.assertIn("UNVERIFIED", second["systemMessage"])

    def test_init_rejects_preexisting_dirty_owned_paths(self) -> None:
        (self.root / "owned.txt").write_text("user edits\n", encoding="utf-8")
        result = self.init("dirty1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("dirty owned paths", result.stderr)

        (self.root / "owned.txt").write_text("base\n", encoding="utf-8")
        (self.root / "new_owned.py").write_text("untracked\n", encoding="utf-8")
        untracked = self.cli("init", "--session", "dirty2", "--cwd", str(self.root),
                             "--base-sha", self.base, "--owned-path", "new_owned.py", "--check", "true")
        self.assertEqual(untracked.returncode, 2)
        self.assertIn("new_owned.py", untracked.stderr)

    def test_high_risk_hook_asks_and_routine_command_has_no_decision(self) -> None:
        def invoke(command: str) -> dict[str, object]:
            result = self.cli("hook-pre", input_text=json.dumps({
                "tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(self.root),
            }))
            return json.loads(result.stdout) if result.stdout else {}

        risky = invoke("git push --force-with-lease origin feature")
        self.assertEqual(risky["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertEqual(invoke("python -m pytest tests/test_unit.py"), {})

    def test_hook_ignores_unrelated_worktree_and_non_repository(self) -> None:
        self.assertEqual(self.init("worktree1").returncode, 0)
        other = Path(self.temp.name) / "other"
        self.run_git("worktree", "add", "--detach", str(other), "HEAD")
        result = self.cli("hook-stop", input_text=json.dumps({
            "session_id": "worktree1", "cwd": str(other),
        }))
        self.assertEqual(result.stdout, "")
        outside = self.cli("hook-stop", input_text=json.dumps({
            "session_id": "worktree1", "cwd": self.temp.name,
        }))
        self.assertEqual(outside.stdout, "")

    def test_hook_git_queries_do_not_run_fsmonitor_diff_or_filter_commands(self) -> None:
        marker = Path(self.temp.name) / "executed-marker"
        (self.root / ".gitattributes").write_text("*.txt filter=a=b\n", encoding="utf-8")
        self.run_git("add", ".gitattributes")
        self.run_git("commit", "-qm", "add filter attribute")
        self.base = self.run_git("rev-parse", "HEAD").stdout.strip()
        self.run_git("config", "core.fsmonitor", f"touch {marker}")
        self.run_git("config", "diff.external", f"touch {marker}")
        self.run_git("config", "filter.a=b.clean", f"touch {marker} && cat")
        # Confirm this unusual driver name is active before checking that the
        # hardened helper disables it, including the '=' in the config key.
        subprocess.run(["git", "-C", str(self.root), "hash-object", "--path=owned.txt", "owned.txt"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertTrue(marker.exists())
        marker.unlink()
        self.run_git("config", "filter.a=b.process", f"touch {marker}")
        self.run_git("config", "filter.a=b.required", "true")
        team_gate.run_git(self.root, "hash-object", "--path=owned.txt", "owned.txt")
        self.assertFalse(marker.exists())
        self.assertEqual(self.init("poison1").returncode, 0)
        (self.root / "owned.txt").write_text("changed\n", encoding="utf-8")
        state = next((self.root / ".git" / "team-runs" / "autonomous-team").glob("poison1-*.json"))
        saved = json.loads(state.read_text(encoding="utf-8"))
        saved["status"] = "ready"
        state.write_text(json.dumps(saved), encoding="utf-8")
        hook = self.hook_stop("poison1")
        self.assertEqual(hook.returncode, 0, hook.stderr)
        self.assertFalse(marker.exists(), hook.stdout)

    def test_hook_ignores_nested_submodule_filter_execution(self) -> None:
        marker = Path(self.temp.name) / "submodule-marker"
        source = Path(self.temp.name) / "nested-source"
        source.mkdir()
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.name", "Gate Test"], check=True)
        subprocess.run(["git", "-C", str(source), "config", "filter.a=b.clean", "cat"], check=True)
        subprocess.run(["git", "-C", str(source), "config", "filter.a=b.required", "true"], check=True)
        (source / ".gitattributes").write_text("*.txt filter=a=b\n", encoding="utf-8")
        (source / "nested.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(source), "commit", "-qm", "nested base"], check=True)
        subprocess.run(["git", "-c", "protocol.file.allow=always", "-C", str(self.root),
                        "submodule", "add", str(source), "nested"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.run_git("commit", "-qm", "add submodule")
        self.base = self.run_git("rev-parse", "HEAD").stdout.strip()
        subprocess.run(["git", "-C", str(self.root / "nested"), "config", "filter.a=b.clean",
                        f"touch {marker}"], check=True)
        (self.root / "nested" / "nested.txt").write_text("modified\n", encoding="utf-8")
        # The child filter is active, but parent gate queries must not inspect
        # dirty submodule contents or invoke the child's configured command.
        subprocess.run(["git", "-C", str(self.root / "nested"), "hash-object",
                        "--path=nested.txt", "nested.txt"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertTrue(marker.exists())
        marker.unlink()
        self.assertEqual(self.init("submodule1").returncode, 0)
        (self.root / "owned.txt").write_text("changed\n", encoding="utf-8")
        state = next((self.root / ".git" / "team-runs" / "autonomous-team").glob("submodule1-*.json"))
        saved = json.loads(state.read_text(encoding="utf-8"))
        saved["status"] = "ready"
        state.write_text(json.dumps(saved), encoding="utf-8")
        result = self.hook_stop("submodule1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists(), result.stdout)


if __name__ == "__main__":
    unittest.main()
