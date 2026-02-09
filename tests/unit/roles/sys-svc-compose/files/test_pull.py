import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _repo_root(start: Path) -> Path:
    # __file__ = tests/unit/roles/sys-svc-compose/files/test_pull.py
    return start.resolve().parents[5]


def _load_module(rel_path: str, name: str) -> ModuleType:
    root = _repo_root(Path(__file__))
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestComposePull(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load_module("roles/sys-svc-compose/files/pull.py", "compose_pull_mod")

    def test_run_cmd_returns_rc_and_output(self) -> None:
        cwd = Path("/")
        env = {}

        class DummyProc:
            def __init__(self, returncode: int, stdout: str) -> None:
                self.returncode = returncode
                self.stdout = stdout

        def fake_run(*args, **kwargs):
            return DummyProc(7, "hello\n")

        with patch.object(self.m.subprocess, "run", side_effect=fake_run):
            rc, out = self.m.run_cmd(["echo", "x"], cwd=cwd, env=env)

        self.assertEqual(rc, 7)
        self.assertEqual(out, "hello\n")

    def test_base_compose_cmd_includes_project_files_and_env(self) -> None:
        cmd = self.m.base_compose_cmd(
            project="p", compose_files="-f a.yml -f b.yml", env_file="/x/.env"
        )
        self.assertEqual(cmd[:4], ["docker", "compose", "-p", "p"])
        self.assertIn("-f", cmd)
        self.assertIn("a.yml", cmd)
        self.assertIn("b.yml", cmd)
        self.assertIn("--env-file", cmd)
        self.assertIn("/x/.env", cmd)

    def test_base_compose_cmd_omits_env_when_empty(self) -> None:
        cmd = self.m.base_compose_cmd(
            project="p", compose_files="-f a.yml", env_file=""
        )
        self.assertEqual(cmd[:4], ["docker", "compose", "-p", "p"])
        self.assertIn("-f", cmd)
        self.assertIn("a.yml", cmd)
        self.assertNotIn("--env-file", cmd)

    def test_has_buildable_services_true(self) -> None:
        config_out = """
services:
  app:
    build:
      context: .
    image: example/app
"""
        base_cmd = ["docker", "compose", "-p", "p", "-f", "a.yml"]
        with patch.object(self.m, "run_cmd", return_value=(0, config_out)):
            self.assertTrue(
                self.m.has_buildable_services(
                    base_cmd=base_cmd, cwd=Path("/tmp"), env={}
                )
            )

    def test_has_buildable_services_false(self) -> None:
        config_out = """
services:
  app:
    image: example/app
"""
        base_cmd = ["docker", "compose", "-p", "p", "-f", "a.yml"]
        with patch.object(self.m, "run_cmd", return_value=(0, config_out)):
            self.assertFalse(
                self.m.has_buildable_services(
                    base_cmd=base_cmd, cwd=Path("/tmp"), env={}
                )
            )

    def test_run_or_fail_success_does_not_raise(self) -> None:
        with patch.object(self.m, "run_cmd", return_value=(0, "ok\n")):
            # Should not raise
            self.m.run_or_fail(
                ["docker", "compose", "ps"], cwd=Path("/"), env={}, label="x"
            )

    def test_run_or_fail_failure_raises(self) -> None:
        with patch.object(self.m, "run_cmd", return_value=(9, "boom\n")):
            with self.assertRaises(RuntimeError) as ctx:
                self.m.run_or_fail(
                    ["docker", "compose", "pull"], cwd=Path("/"), env={}, label="pull"
                )
        self.assertIn("pull failed", str(ctx.exception))

    def test_main_short_circuits_when_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock_dir = Path(td) / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_key = "abc123"
            (lock_dir / f"{lock_key}.lock").write_text("ok\n", encoding="utf-8")

            argv = [
                "pull.py",
                "--chdir",
                td,
                "--project",
                "p",
                "--compose-files",
                "-f a.yml -f b.yml",
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(self.m, "run_or_fail") as rof_mock,
                patch.object(self.m, "has_buildable_services") as hbs_mock,
            ):
                rc = self.m.main()

            self.assertEqual(rc, 0)
            rof_mock.assert_not_called()
            hbs_mock.assert_not_called()

    def test_main_runs_build_and_pull_and_writes_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chdir = Path(td) / "instance"
            chdir.mkdir(parents=True, exist_ok=True)

            lock_dir = Path(td) / "locks"
            lock_key = "k1"

            argv = [
                "pull.py",
                "--chdir",
                str(chdir),
                "--project",
                "p",
                "--compose-files",
                "-f a.yml -f b.yml",
                "--env-file",
                "/x/.env",
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
                "--ignore-buildable",
            ]

            base_cmd = [
                "docker",
                "compose",
                "-p",
                "p",
                "-f",
                "a.yml",
                "-f",
                "b.yml",
                "--env-file",
                "/x/.env",
            ]

            def fake_run_cmd(
                cmd: list[str], *, cwd: Path, env: dict[str, str]
            ) -> tuple[int, str]:
                # main() probes pull --help to detect --ignore-buildable support
                if cmd[-2:] == ["pull", "--help"]:
                    return 0, "Usage:\n  --ignore-buildable\n"
                return 0, ""

            calls: list[list[str]] = []

            def fake_run_or_fail(
                cmd: list[str], *, cwd: Path, env: dict[str, str], label: str
            ) -> None:
                calls.append(cmd)

            with (
                patch.object(sys, "argv", argv),
                patch.object(self.m, "has_buildable_services", return_value=True),
                patch.object(self.m, "run_cmd", side_effect=fake_run_cmd),
                patch.object(self.m, "base_compose_cmd", return_value=base_cmd),
                patch.object(self.m, "run_or_fail", side_effect=fake_run_or_fail),
            ):
                rc = self.m.main()

            self.assertEqual(rc, 0)
            self.assertTrue(
                (lock_dir / f"{lock_key}.lock").exists(),
                "lock file should be written on success",
            )

            # Expect two calls: build --pull, then pull --ignore-buildable
            self.assertEqual(calls[0], base_cmd + ["build", "--pull"])
            self.assertEqual(calls[1], base_cmd + ["pull", "--ignore-buildable"])

    def test_main_pull_omits_ignore_buildable_when_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chdir = Path(td) / "instance"
            chdir.mkdir(parents=True, exist_ok=True)

            lock_dir = Path(td) / "locks"
            lock_key = "k2"

            argv = [
                "pull.py",
                "--chdir",
                str(chdir),
                "--project",
                "p",
                "--compose-files",
                "-f a.yml",
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
                "--ignore-buildable",
            ]

            base_cmd = ["docker", "compose", "-p", "p", "-f", "a.yml"]

            def fake_run_cmd(
                cmd: list[str], *, cwd: Path, env: dict[str, str]
            ) -> tuple[int, str]:
                if cmd[-2:] == ["pull", "--help"]:
                    return 0, "Usage:\n"  # no --ignore-buildable mentioned
                return 0, ""

            calls: list[list[str]] = []

            def fake_run_or_fail(
                cmd: list[str], *, cwd: Path, env: dict[str, str], label: str
            ) -> None:
                calls.append(cmd)

            with (
                patch.object(sys, "argv", argv),
                patch.object(self.m, "has_buildable_services", return_value=False),
                patch.object(self.m, "run_cmd", side_effect=fake_run_cmd),
                patch.object(self.m, "base_compose_cmd", return_value=base_cmd),
                patch.object(self.m, "run_or_fail", side_effect=fake_run_or_fail),
            ):
                rc = self.m.main()

            self.assertEqual(rc, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], base_cmd + ["pull"])


if __name__ == "__main__":
    unittest.main()
