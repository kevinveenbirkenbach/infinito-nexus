# tests/unit/roles/docker-compose/files/test_compose_pull.py
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _repo_root(start: Path) -> Path:
    # __file__ = tests/unit/roles/docker-compose/files/test_compose_pull.py
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
    def setUp(self):
        self.m = _load_module(
            "roles/docker-compose/files/compose_pull.py", "compose_pull_mod"
        )

    def test_transient_regex_matches(self):
        self.assertTrue(self.m.TRANSIENT_RE.search("TLS handshake timeout"))
        self.assertTrue(self.m.TRANSIENT_RE.search("Could not resolve host"))
        self.assertTrue(self.m.TRANSIENT_RE.search("unexpected EOF"))
        self.assertFalse(self.m.TRANSIENT_RE.search("permission denied"))

    def test_run_cmd_returns_rc_and_output(self):
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

    def test_base_compose_cmd_includes_project_files_and_env(self):
        cmd = self.m.base_compose_cmd(
            project="p", compose_files="-f a.yml -f b.yml", env_file="/x/.env"
        )
        self.assertEqual(cmd[:4], ["docker", "compose", "-p", "p"])
        self.assertIn("-f", cmd)
        self.assertIn("a.yml", cmd)
        self.assertIn("b.yml", cmd)
        self.assertIn("--env-file", cmd)
        self.assertIn("/x/.env", cmd)

    def test_base_compose_cmd_omits_env_when_empty(self):
        cmd = self.m.base_compose_cmd(
            project="p", compose_files="-f a.yml", env_file=""
        )
        self.assertEqual(cmd[:4], ["docker", "compose", "-p", "p"])
        self.assertIn("-f", cmd)
        self.assertIn("a.yml", cmd)
        self.assertNotIn("--env-file", cmd)

    def test_retry_success_first_try_no_sleep(self):
        with (
            patch.object(self.m, "run_cmd", return_value=(0, "ok\n")) as run_cmd,
            patch.object(self.m.time, "sleep") as sleep,
        ):
            self.m.retry(
                ["docker", "compose", "pull"],
                cwd=Path("/"),
                env={},
                attempts=3,
                sleep_s=0.1,
                sleep_cap_s=1.0,
            )

        run_cmd.assert_called_once()
        sleep.assert_not_called()

    def test_retry_transient_then_success_sleeps_once(self):
        side_effects = [
            (1, 'Get "https://registry-1.docker.io/v2/": TLS handshake timeout'),
            (0, "done\n"),
        ]
        with (
            patch.object(self.m, "run_cmd", side_effect=side_effects) as run_cmd,
            patch.object(self.m.time, "sleep") as sleep,
        ):
            self.m.retry(
                ["docker", "compose", "pull"],
                cwd=Path("/"),
                env={},
                attempts=6,
                sleep_s=2.0,
                sleep_cap_s=60.0,
            )

        self.assertEqual(run_cmd.call_count, 2)
        sleep.assert_called_once_with(2.0)

    def test_retry_non_transient_raises(self):
        with (
            patch.object(
                self.m, "run_cmd", return_value=(1, "unauthorized: access denied")
            ),
            patch.object(self.m.time, "sleep") as sleep,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                self.m.retry(
                    ["docker", "compose", "pull"],
                    cwd=Path("/"),
                    env={},
                    attempts=6,
                    sleep_s=2.0,
                    sleep_cap_s=60.0,
                )
        self.assertIn("Non-transient failure", str(ctx.exception))
        sleep.assert_not_called()

    def test_retry_exhausts_attempts_raises(self):
        # 3 attempts -> 2 sleeps
        with (
            patch.object(
                self.m,
                "run_cmd",
                side_effect=[
                    (1, "TLS handshake timeout"),
                    (1, "TLS handshake timeout"),
                    (1, "TLS handshake timeout"),
                ],
            ),
            patch.object(self.m.time, "sleep") as sleep,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                self.m.retry(
                    ["docker", "compose", "pull"],
                    cwd=Path("/"),
                    env={},
                    attempts=3,
                    sleep_s=1.0,
                    sleep_cap_s=60.0,
                )

        self.assertIn("Transient failure persisted", str(ctx.exception))
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_any_call(1.0)
        sleep.assert_any_call(2.0)

    def test_has_buildable_services_true(self):
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

    def test_has_buildable_services_false(self):
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

    def test_main_short_circuits_when_lock_exists(self):
        with tempfile.TemporaryDirectory() as td:
            lock_dir = Path(td) / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_key = "abc123"
            (lock_dir / f"{lock_key}.lock").write_text("ok\n", encoding="utf-8")

            argv = [
                "compose_pull.py",
                "--chdir",
                td,
                "--project",
                "p",
                "--compose-files",
                "-f a.yml -f b.yml",
                "--env-file",
                "",  # optional
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(self.m, "retry") as retry_mock,
                patch.object(self.m, "has_buildable_services") as hbs_mock,
            ):
                rc = self.m.main()

            self.assertEqual(rc, 0)
            retry_mock.assert_not_called()
            hbs_mock.assert_not_called()

    def test_main_runs_build_and_pull_and_writes_lock(self):
        with tempfile.TemporaryDirectory() as td:
            chdir = Path(td) / "instance"
            chdir.mkdir(parents=True, exist_ok=True)

            lock_dir = Path(td) / "locks"
            lock_key = "k1"

            calls: list[list[str]] = []

            def fake_retry(cmd, *, cwd, env, attempts, sleep_s, sleep_cap_s) -> None:
                calls.append(cmd)

            def fake_run_cmd(
                cmd: list[str], *, cwd: Path, env: dict[str, str]
            ) -> tuple[int, str]:
                # only used by main() to check pull --help when ignore_buildable is requested
                if cmd[-2:] == ["pull", "--help"]:
                    return 0, "Usage:\n  --ignore-buildable\n"
                return 0, ""

            argv = [
                "compose_pull.py",
                "--chdir",
                str(chdir),
                "--project",
                "p",
                "--compose-files",
                "-f a.yml -f b.yml",
                "--env-file",
                "/x/.env",  # optional
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
                "--attempts",
                "2",
                "--sleep",
                "0.01",
                "--sleep-cap",
                "0.02",
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

            with (
                patch.object(sys, "argv", argv),
                patch.object(self.m, "has_buildable_services", return_value=True),
                patch.object(self.m, "retry", side_effect=fake_retry),
                patch.object(self.m, "run_cmd", side_effect=fake_run_cmd),
                patch.object(self.m, "base_compose_cmd", return_value=base_cmd),
            ):
                rc = self.m.main()

            self.assertEqual(rc, 0)
            self.assertTrue(
                (lock_dir / f"{lock_key}.lock").exists(),
                "lock file should be written on success",
            )

            # Expect two retry calls: build --pull, then pull --ignore-buildable
            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(calls[0], base_cmd + ["build", "--pull"])
            self.assertEqual(calls[1], base_cmd + ["pull", "--ignore-buildable"])


if __name__ == "__main__":
    unittest.main()
