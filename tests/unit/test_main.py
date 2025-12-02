import os
import sys
import tempfile
import unittest
from unittest import mock

# Insert project root into import path so we can import main.py
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

import main  # assumes main.py lives at the project root


class TestMainHelpers(unittest.TestCase):

    # ----------------------
    # Existing tests …
    # ----------------------

    @mock.patch.object(main, 'Style')
    def test_color_text_wraps_text_with_color_and_reset(self, mock_style):
        """
        color_text() should wrap text with the given color prefix and Style.RESET_ALL.
        We patch Style.RESET_ALL to produce deterministic output.
        """
        mock_style.RESET_ALL = '<RESET>'
        result = main.color_text("Hello", "<C>")
        self.assertEqual(result, "<C>Hello<RESET>")

    def test_list_cli_commands_with_nested_directories(self):
        """
        list_cli_commands() should correctly identify CLI commands inside
        nested directories and return folder paths using '/' separators.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # File in root directory
            root_cmd = os.path.join(tmpdir, "rootcmd.py")
            with open(root_cmd, "w") as f:
                f.write("import argparse\n")

            # File in nested directory: sub/innercmd.py
            sub = os.path.join(tmpdir, "sub")
            os.makedirs(sub, exist_ok=True)
            nested_cmd = os.path.join(sub, "innercmd.py")
            with open(nested_cmd, "w") as f:
                f.write("import argparse\n")

            commands = main.list_cli_commands(tmpdir)

            self.assertIn((None, "rootcmd"), commands)
            self.assertIn(("sub", "innercmd"), commands)

    @mock.patch('main.subprocess.run', side_effect=Exception("mocked error"))
    def test_extract_description_via_help_returns_dash_on_exception(self, mock_run):
        """
        extract_description_via_help() should return '-' if subprocess.run
        raises any exception.
        """
        result = main.extract_description_via_help("/fake/path/script.py")
        self.assertEqual(result, "-")

    @mock.patch('main.subprocess.run')
    def test_show_full_help_for_all_invokes_help_for_each_command(self, mock_run):
        """
        show_full_help_for_all() should execute a help subprocess call for each
        discovered CLI command. The module path must be correct.
        """
        available = [
            (None, "deploy"),
            ("build/defaults", "users"),
        ]

        main.show_full_help_for_all("/fake/cli", available)

        expected_modules = {"cli.deploy", "cli.build.defaults.users"}
        invoked_modules = set()

        for call in mock_run.call_args_list:
            args, kwargs = call
            cmd = args[0]

            # Validate invocation structure
            self.assertGreaterEqual(len(cmd), 3)
            self.assertEqual(cmd[1], "-m")       # Second argument must be '-m'
            invoked_modules.add(cmd[2])          # Module name

            # Validate flags
            self.assertEqual(kwargs.get("capture_output"), True)
            self.assertEqual(kwargs.get("text"), True)
            self.assertEqual(kwargs.get("check"), False)

        self.assertEqual(expected_modules, invoked_modules)

    def test_format_command_help_basic(self):
        name = "cmd"
        description = "A basic description"
        output = main.format_command_help(
            name, description,
            indent=2, col_width=20, width=40
        )
        # Should start with two spaces and the command name
        self.assertTrue(output.startswith("  cmd"))
        # Description should appear somewhere in the wrapped text
        self.assertIn("A basic description", output)

    def test_list_cli_commands_filters_and_sorts(self):
        # Create a temporary directory with sample files containing argparse
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python files that import argparse
            one_path = os.path.join(tmpdir, "one.py")
            with open(one_path, "w") as f:
                f.write("import argparse\n# dummy CLI command\n")

            two_path = os.path.join(tmpdir, "two.py")
            with open(two_path, "w") as f:
                f.write("import argparse\n# another CLI command\n")

            # Non-Python and dunder files should be ignored
            open(os.path.join(tmpdir, "__init__.py"), "w").close()
            open(os.path.join(tmpdir, "ignore.txt"), "w").close()

            # Only 'one' and 'two' should be returned, in sorted order
            commands = main.list_cli_commands(tmpdir)
            self.assertEqual([(None, 'one'), (None, 'two')], commands)

    def test_git_clean_repo_invokes_git_clean(self):
        with mock.patch('main.subprocess.run') as mock_run:
            main.git_clean_repo()
            mock_run.assert_called_once_with(['git', 'clean', '-Xfd'], check=True)

    @mock.patch('main.subprocess.run')
    def test_extract_description_via_help_with_description(self, mock_run):
        # Simulate subprocess returning help output with a description
        mock_stdout = "usage: dummy.py [options]\n\nThis is a help description.\n"
        mock_run.return_value = mock.Mock(stdout=mock_stdout)
        description = main.extract_description_via_help("/fake/path/dummy.py")
        self.assertEqual(description, "This is a help description.")

    @mock.patch('main.subprocess.run')
    def test_extract_description_via_help_without_description(self, mock_run):
        # Simulate subprocess returning help output without a description
        mock_stdout = "usage: empty.py [options]\n"
        mock_run.return_value = mock.Mock(stdout=mock_stdout)
        description = main.extract_description_via_help("/fake/path/empty.py")
        self.assertEqual(description, "-")


if __name__ == "__main__":
    unittest.main()
