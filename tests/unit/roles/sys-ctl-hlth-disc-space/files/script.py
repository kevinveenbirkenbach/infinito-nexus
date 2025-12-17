#!/usr/bin/env python3
import io
import sys
import unittest
import pathlib
import contextlib
import importlib.util
from types import SimpleNamespace
from unittest import mock


def load_target_module():
    """
    Load the target script (roles/sys-ctl-hlth-disc-space/files/script.py)
    via its file path so that dashes in the directory name are not an issue.
    """
    # tests/unit/roles/sys-ctl-hlth-disc-space/files/script.py
    test_file_path = pathlib.Path(__file__).resolve()
    repo_root = test_file_path.parents[
        4
    ]  # go up: files -> ... -> unit -> tests -> <root>

    script_path = (
        repo_root / "roles" / "sys-ctl-hlth-disc-space" / "files" / "script.py"
    )
    if not script_path.is_file():
        raise FileNotFoundError(f"Target script not found at: {script_path}")

    spec = importlib.util.spec_from_file_location("disk_space_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# Load the module once for all tests
SCRIPT_MODULE = load_target_module()


class TestDiskSpaceScript(unittest.TestCase):
    def test_get_disk_usage_percentages_parses_output(self):
        """
        Ensure get_disk_usage_percentages parses 'df --output=pcent' correctly
        and returns integer percentages without the '%' sign.
        """
        # Fake df output, including header line and various spacings
        fake_df_output = "Use%\n 10%\n  50%\n100%\n"

        with mock.patch.object(
            SCRIPT_MODULE.subprocess,
            "run",
            return_value=SimpleNamespace(stdout=fake_df_output, returncode=0),
        ):
            result = SCRIPT_MODULE.get_disk_usage_percentages()

        self.assertEqual(result, [10, 50, 100])

    def test_main_exits_zero_when_below_threshold(self):
        """
        If all filesystems are below or equal the threshold,
        main() should exit with status code 0.
        """
        # First call: 'df' (printing only) -> we don't care about stdout here
        df_print_cp = SimpleNamespace(stdout="Filesystem ...\n", returncode=0)
        # Second call: 'df --output=pcent'
        df_pcent_cp = SimpleNamespace(stdout="Use%\n 10%\n 50%\n 80%\n", returncode=0)

        def fake_run(args, capture_output=False, text=False, check=False):
            # Decide which fake result to return based on the arguments
            if args == ["df", "--output=pcent"]:
                return df_pcent_cp
            elif args == ["df"]:
                return df_print_cp
            else:
                raise AssertionError(f"Unexpected subprocess.run args: {args}")

        with mock.patch.object(SCRIPT_MODULE.subprocess, "run", side_effect=fake_run):
            with mock.patch.object(sys, "argv", ["script.py", "80"]):
                with mock.patch.object(
                    SCRIPT_MODULE.sys, "exit", side_effect=SystemExit
                ) as mock_exit:
                    # Capture stdout to avoid clutter in test output
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(SystemExit):
                            SCRIPT_MODULE.main()

        # Expect no filesystem above 80% -> exit code 0
        mock_exit.assert_called_once_with(0)

    def test_main_exits_with_error_count_and_prints_warnings(self):
        """
        If some filesystems exceed the threshold, main() should:
        - Print a warning for each filesystem that exceeds it
        - Exit with a status code equal to the number of such filesystems
        """
        df_print_cp = SimpleNamespace(stdout="Filesystem ...\n", returncode=0)
        # Two filesystems above threshold (90%, 95%), one below (60%)
        df_pcent_cp = SimpleNamespace(stdout="Use%\n 60%\n 90%\n 95%\n", returncode=0)

        def fake_run(args, capture_output=False, text=False, check=False):
            if args == ["df", "--output=pcent"]:
                return df_pcent_cp
            elif args == ["df"]:
                return df_print_cp
            else:
                raise AssertionError(f"Unexpected subprocess.run args: {args}")

        with mock.patch.object(SCRIPT_MODULE.subprocess, "run", side_effect=fake_run):
            with mock.patch.object(sys, "argv", ["script.py", "80"]):
                with mock.patch.object(
                    SCRIPT_MODULE.sys, "exit", side_effect=SystemExit
                ) as mock_exit:
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        with self.assertRaises(SystemExit):
                            SCRIPT_MODULE.main()

        # Expect exit code 2 (two filesystems over 80%)
        mock_exit.assert_called_once_with(2)

        output = buffer.getvalue()
        self.assertIn("Checking disk space usage...", output)
        self.assertIn("WARNING: 90% exceeds the limit of 80%.", output)
        self.assertIn("WARNING: 95% exceeds the limit of 80%.", output)
        # Ensure the "below threshold" value does not produce a warning
        self.assertNotIn("60% exceeds the limit of 80%.", output)


if __name__ == "__main__":
    unittest.main()
