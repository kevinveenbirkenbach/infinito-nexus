# tests/cli/deploy/development/test_compose.py
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cli.deploy.development.compose import Compose


class TestComposeUpRetries(unittest.TestCase):
    def _compose(self) -> Compose:
        # repo_root is only used as a cwd in subprocess calls; for these unit tests
        # we do not execute real subprocesses.
        return Compose(repo_root=Path("/tmp/infinito-nexus"), distro="arch")

    @patch("time.sleep", autospec=True)
    def test_compose_up_with_retries_succeeds_after_transient_failures(
        self, sleep_mock: MagicMock
    ) -> None:
        compose = self._compose()

        # Fail 2 times, then succeed.
        compose.run = MagicMock(
            side_effect=[
                subprocess.CalledProcessError(1, ["docker", "compose"], "out1", "err1"),
                subprocess.CalledProcessError(1, ["docker", "compose"], "out2", "err2"),
                subprocess.CompletedProcess(
                    ["docker", "compose"], 0, stdout="", stderr=""
                ),
            ]
        )

        args = ["--env-file", "env.ci", "up", "-d", "--no-build", "coredns", "infinito"]
        compose._compose_up_with_retries(args, attempts=6, delay_s=30)

        # 3 calls: fail, fail, succeed
        self.assertEqual(compose.run.call_count, 3)

        # Sleep after each failure (2 times), not after success
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(30)
        # Ensure all sleeps used exactly 30 seconds
        self.assertTrue(all(call.args == (30,) for call in sleep_mock.call_args_list))

    @patch("time.sleep", autospec=True)
    def test_compose_up_with_retries_raises_after_exhausting_attempts(
        self, sleep_mock: MagicMock
    ) -> None:
        compose = self._compose()

        # Always fail.
        compose.run = MagicMock(
            side_effect=subprocess.CalledProcessError(
                1, ["docker", "compose"], "out", "err"
            )
        )

        args = ["--env-file", "env.ci", "up", "-d", "coredns", "infinito"]

        with self.assertRaises(subprocess.CalledProcessError):
            compose._compose_up_with_retries(args, attempts=6, delay_s=30)

        # Called exactly 6 times
        self.assertEqual(compose.run.call_count, 6)

        # Sleep between attempts: after attempts 1..5 => 5 sleeps
        self.assertEqual(sleep_mock.call_count, 5)
        self.assertTrue(all(call.args == (30,) for call in sleep_mock.call_args_list))

    @patch("time.sleep", autospec=True)
    def test_compose_up_with_retries_no_sleep_if_first_try_succeeds(
        self, sleep_mock: MagicMock
    ) -> None:
        compose = self._compose()

        compose.run = MagicMock(
            return_value=subprocess.CompletedProcess(
                ["docker", "compose"], 0, stdout="", stderr=""
            )
        )

        args = ["--env-file", "env.ci", "up", "-d", "coredns", "infinito"]
        compose._compose_up_with_retries(args, attempts=6, delay_s=30)

        self.assertEqual(compose.run.call_count, 1)
        sleep_mock.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
