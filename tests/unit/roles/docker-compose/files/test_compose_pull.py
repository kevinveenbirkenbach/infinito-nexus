# tests/unit/roles/docker-compose/files/test_compose_pull.py
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _load_compose_pull_module() -> ModuleType:
    """
    Load roles/docker-compose/files/compose_pull.py as a Python module.

    We cannot import it as a normal package module because the path contains
    a hyphen (docker-compose).
    """
    repo_root = Path(__file__).resolve().parents[5]
    script_path = repo_root / "roles" / "docker-compose" / "files" / "compose_pull.py"
    if not script_path.is_file():
        raise FileNotFoundError(f"compose_pull.py not found at: {script_path}")

    spec = importlib.util.spec_from_file_location("compose_pull", str(script_path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


compose_pull = _load_compose_pull_module()


class TestComposePull(unittest.TestCase):
    def test_run_cmd_returns_rc_and_output(self) -> None:
        cwd = Path("/")
        env = {}

        class DummyProc:
            def __init__(self, returncode: int, stdout: str) -> None:
                self.returncode = returncode
                self.stdout = stdout

        def fake_run(*args, **kwargs):
            return DummyProc(7, "hello\n")

        with patch.object(compose_pull.subprocess, "run", side_effect=fake_run):
            rc, out = compose_pull.run_cmd(["echo", "x"], cwd=cwd, env=env)

        self.assertEqual(rc, 7)
        self.assertEqual(out, "hello\n")

    def test_retry_success_first_try_no_sleep(self) -> None:
        with (
            patch.object(compose_pull, "run_cmd", return_value=(0, "ok\n")) as run_cmd,
            patch.object(compose_pull.time, "sleep") as sleep,
        ):
            compose_pull.retry(
                ["docker", "compose", "pull"],
                cwd=Path("/"),
                env={},
                attempts=3,
                sleep_s=0.1,
                sleep_cap_s=1.0,
            )

        run_cmd.assert_called_once()
        sleep.assert_not_called()

    def test_retry_transient_then_success_sleeps_once(self) -> None:
        side_effects = [
            (1, 'Get "https://registry-1.docker.io/v2/": TLS handshake timeout'),
            (0, "done\n"),
        ]
        with (
            patch.object(compose_pull, "run_cmd", side_effect=side_effects) as run_cmd,
            patch.object(compose_pull.time, "sleep") as sleep,
        ):
            compose_pull.retry(
                ["docker", "compose", "pull"],
                cwd=Path("/"),
                env={},
                attempts=5,
                sleep_s=2.0,
                sleep_cap_s=60.0,
            )

        self.assertEqual(run_cmd.call_count, 2)
        sleep.assert_called_once_with(2.0)

    def test_retry_non_transient_raises(self) -> None:
        with (
            patch.object(
                compose_pull, "run_cmd", return_value=(1, "unauthorized: access denied")
            ),
            patch.object(compose_pull.time, "sleep") as sleep,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                compose_pull.retry(
                    ["docker", "compose", "pull"],
                    cwd=Path("/"),
                    env={},
                    attempts=6,
                    sleep_s=2.0,
                    sleep_cap_s=60.0,
                )
        self.assertIn("Non-transient failure", str(ctx.exception))
        sleep.assert_not_called()

    def test_retry_exhausts_attempts_raises(self) -> None:
        # 3 attempts -> 2 sleeps
        with (
            patch.object(
                compose_pull,
                "run_cmd",
                side_effect=[
                    (1, "TLS handshake timeout"),
                    (1, "TLS handshake timeout"),
                    (1, "TLS handshake timeout"),
                ],
            ),
            patch.object(compose_pull.time, "sleep") as sleep,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                compose_pull.retry(
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

    def test_has_buildable_services_true(self) -> None:
        config_out = """
services:
  app:
    build:
      context: .
    image: example/app
"""
        with patch.object(compose_pull, "run_cmd", return_value=(0, config_out)):
            self.assertTrue(
                compose_pull.has_buildable_services(cwd=Path("/tmp"), env={})
            )

    def test_has_buildable_services_false(self) -> None:
        config_out = """
services:
  app:
    image: example/app
"""
        with patch.object(compose_pull, "run_cmd", return_value=(0, config_out)):
            self.assertFalse(
                compose_pull.has_buildable_services(cwd=Path("/tmp"), env={})
            )

    def test_main_short_circuits_when_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock_dir = Path(td) / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_key = "abc123"
            (lock_dir / f"{lock_key}.lock").write_text("ok\n", encoding="utf-8")

            argv = [
                "compose_pull.py",
                "--chdir",
                td,
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(compose_pull, "retry") as retry_mock,
                patch.object(compose_pull, "has_buildable_services") as hbs_mock,
            ):
                rc = compose_pull.main()

            self.assertEqual(rc, 0)
            retry_mock.assert_not_called()
            hbs_mock.assert_not_called()

    def test_main_runs_build_and_pull_and_writes_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chdir = Path(td) / "instance"
            chdir.mkdir(parents=True, exist_ok=True)

            lock_dir = Path(td) / "locks"
            lock_key = "k1"

            calls: list[list[str]] = []

            def fake_retry(cmd, *, cwd, env, attempts, sleep_s, sleep_cap_s) -> None:
                # record the actual command list passed
                calls.append(cmd)

            def fake_run_cmd(
                cmd: list[str], *, cwd: Path, env: dict[str, str]
            ) -> tuple[int, str]:
                # only used by main() to check pull --help
                if cmd[:4] == ["docker", "compose", "pull", "--help"]:
                    return 0, "Usage:\n  --ignore-buildable\n"
                return 0, ""

            argv = [
                "compose_pull.py",
                "--chdir",
                str(chdir),
                "--lock-dir",
                str(lock_dir),
                "--lock-key",
                lock_key,
                "--attempts",
                "2",
                "--sleep",
                "0.01",
                "--ignore-buildable",
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(compose_pull, "has_buildable_services", return_value=True),
                patch.object(compose_pull, "retry", side_effect=fake_retry),
                patch.object(compose_pull, "run_cmd", side_effect=fake_run_cmd),
            ):
                rc = compose_pull.main()

            self.assertEqual(rc, 0)
            self.assertTrue(
                (lock_dir / f"{lock_key}.lock").exists(),
                "lock file should be written on success",
            )

            # Expect two retry calls: build --pull, then pull --ignore-buildable
            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(calls[0], ["docker", "compose", "build", "--pull"])
            self.assertEqual(
                calls[1], ["docker", "compose", "pull", "--ignore-buildable"]
            )


if __name__ == "__main__":
    unittest.main()
