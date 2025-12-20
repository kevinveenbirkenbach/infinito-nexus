import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cli.core.discovery import Command
from cli.core.help import (
    extract_description_via_help,
    format_command_help,
    show_full_help_for_all,
    show_help_for_directory,
)


class TestHelp(unittest.TestCase):
    def test_format_command_help_basic(self):
        output = format_command_help(
            name="cmd",
            description="A basic description",
            indent=2,
            col_width=20,
            width=40,
        )
        self.assertTrue(output.startswith("  cmd"))
        self.assertIn("A basic description", output)

    @patch("cli.core.help.subprocess.run", side_effect=Exception("mocked error"))
    def test_extract_description_via_help_returns_dash_on_exception(self, _mock_run):
        self.assertEqual(extract_description_via_help("cli.fake.module"), "-")

    @patch("cli.core.help.subprocess.run")
    def test_extract_description_via_help_with_description(self, mock_run):
        mock_stdout = "usage: dummy [options]\n\nThis is a help description.\n"
        mock_run.return_value = Mock(stdout=mock_stdout, stderr="")
        self.assertEqual(
            extract_description_via_help("cli.some.cmd"),
            "This is a help description.",
        )

    @patch("cli.core.help.subprocess.run")
    def test_extract_description_via_help_without_description(self, mock_run):
        mock_stdout = "usage: empty [options]\n"
        mock_run.return_value = Mock(stdout=mock_stdout, stderr="")
        self.assertEqual(extract_description_via_help("cli.some.cmd"), "-")

    @patch("cli.core.help.discover_commands")
    @patch("cli.core.help.subprocess.run")
    def test_show_full_help_for_all_invokes_help_for_each_command(
        self, mock_run, mock_discover
    ):
        with tempfile.TemporaryDirectory() as td:
            cli_dir = Path(td) / "cli"
            cli_dir.mkdir(parents=True, exist_ok=True)

            cmds = [
                Command(
                    parts=("deploy",),
                    module="cli.deploy",
                    main_path=cli_dir / "deploy" / "__main__.py",
                ),
                Command(
                    parts=("setup", "users"),
                    module="cli.setup.users",
                    main_path=cli_dir / "setup" / "users" / "__main__.py",
                ),
            ]
            mock_discover.return_value = cmds

            show_full_help_for_all(cli_dir)

            invoked_modules = {call.args[0][2] for call in mock_run.call_args_list}
            self.assertEqual({"cli.deploy", "cli.setup.users"}, invoked_modules)

            for call in mock_run.call_args_list:
                args, kwargs = call
                cmd = args[0]
                self.assertGreaterEqual(len(cmd), 4)
                self.assertEqual(cmd[1], "-m")
                self.assertEqual(cmd[3], "--help")
                self.assertEqual(kwargs.get("capture_output"), True)
                self.assertEqual(kwargs.get("text"), True)
                self.assertEqual(kwargs.get("check"), False)

    @patch("cli.core.help.discover_commands")
    @patch("cli.core.help.extract_description_via_help", return_value="DESC")
    @patch("builtins.print")
    def test_show_help_for_directory_lists_only_direct_children(
        self, _mock_print, _mock_extract, mock_discover
    ):
        with tempfile.TemporaryDirectory() as td:
            cli_dir = Path(td) / "cli"
            cli_dir.mkdir(parents=True, exist_ok=True)
            (cli_dir / "meta" / "j2").mkdir(parents=True, exist_ok=True)

            mock_discover.return_value = [
                Command(
                    parts=("meta", "j2", "compiler"),
                    module="cli.meta.j2.compiler",
                    main_path=cli_dir / "meta" / "j2" / "compiler" / "__main__.py",
                ),
                Command(
                    parts=("meta", "applications", "all"),
                    module="cli.meta.applications.all",
                    main_path=cli_dir / "meta" / "applications" / "all" / "__main__.py",
                ),
            ]

            ok = show_help_for_directory(cli_dir, ["meta", "j2"])
            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
