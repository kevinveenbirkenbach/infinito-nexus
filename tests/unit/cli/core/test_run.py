import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli.core.run import RunConfig, open_log_file, run_command_once


class TestRun(unittest.TestCase):
    def test_open_log_file_creates_in_state_home(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["XDG_STATE_HOME"] = td

            f, path = open_log_file()
            try:
                self.assertTrue(path.exists())
                self.assertIn(Path(td), path.parents)
            finally:
                f.close()

    @patch("cli.core.run.subprocess.Popen")
    @patch("cli.core.run.failure_with_warning_loop", side_effect=SystemExit(1))
    def test_run_command_once_nonzero_exits(self, mock_alarm, mock_popen):
        proc = unittest.mock.Mock()
        proc.wait.return_value = None
        proc.returncode = 2
        mock_popen.return_value = proc

        cfg = RunConfig(
            no_signal=True, sound_enabled=False, alarm_timeout=1, log_enabled=False
        )

        with self.assertRaises(SystemExit):
            run_command_once(["python", "-c", "print(1)"], cfg, log_file=None)

        mock_alarm.assert_called_once()

    @patch("cli.core.run.subprocess.Popen")
    def test_run_command_once_success_returns_true(self, mock_popen):
        proc = unittest.mock.Mock()
        proc.wait.return_value = None
        proc.returncode = 0
        mock_popen.return_value = proc

        cfg = RunConfig(
            no_signal=True, sound_enabled=False, alarm_timeout=1, log_enabled=False
        )

        ok = run_command_once(["python", "-c", "print(1)"], cfg, log_file=None)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
