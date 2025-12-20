import sys
import unittest
from unittest.mock import patch

from cli.core.app import parse_flags, main as app_main


class TestApp(unittest.TestCase):
    def test_parse_flags_log_only_for_deploy(self):
        argv = ["infinito", "--log", "build", "tree"]
        flags = parse_flags(argv)
        self.assertFalse(flags.log_enabled)
        self.assertNotIn("--log", argv)

        argv2 = ["infinito", "--log", "deploy", "container"]
        flags2 = parse_flags(argv2)
        self.assertTrue(flags2.log_enabled)
        self.assertIn("--log", argv2)

    def test_parse_flags_alarm_timeout(self):
        argv = ["infinito", "--alarm-timeout", "5", "deploy", "container"]
        flags = parse_flags(argv)
        self.assertEqual(flags.alarm_timeout, 5)
        self.assertNotIn("--alarm-timeout", argv)

    @patch("cli.core.app.init_multiprocessing")
    @patch(
        "cli.core.app.resolve_command_module",
        return_value=("cli.deploy.container", ["--x"]),
    )
    @patch("cli.core.app.run_command_once", return_value=True)
    def test_app_main_dispatches_to_resolved_module(
        self, _mock_run, _mock_resolve, _mock_init
    ):
        old_argv = sys.argv
        try:
            sys.argv = ["infinito", "deploy", "container", "--x"]
            with self.assertRaises(SystemExit) as cm:
                app_main()
            self.assertEqual(cm.exception.code, 0)
        finally:
            sys.argv = old_argv

    @patch("cli.core.app.init_multiprocessing")
    @patch("cli.core.app.resolve_command_module", return_value=(None, ["nope"]))
    def test_app_main_unknown_command_exits_1(self, _mock_resolve, _mock_init):
        old_argv = sys.argv
        try:
            sys.argv = ["infinito", "nope"]
            with self.assertRaises(SystemExit) as cm:
                app_main()
            self.assertEqual(cm.exception.code, 1)
        finally:
            sys.argv = old_argv

    @patch("cli.core.app.init_multiprocessing")
    @patch("cli.core.app.print_global_help")
    def test_app_main_global_help(self, mock_help, _mock_init):
        old_argv = sys.argv
        try:
            sys.argv = ["infinito", "--help"]
            with self.assertRaises(SystemExit) as cm:
                app_main()
            self.assertEqual(cm.exception.code, 0)
            self.assertTrue(mock_help.called)
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
