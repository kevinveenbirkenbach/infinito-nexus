import os
import tempfile
import unittest
import cli.__main__ as main


class TestMainHelpers(unittest.TestCase):
    # ----------------------
    # Existing tests …
    # ----------------------

    @unittest.mock.patch("cli.__main__.Style")
    def test_color_text_wraps_text_with_color_and_reset(self, mock_style):
        """
        color_text() should wrap text with the given color prefix and Style.RESET_ALL.
        We patch Style.RESET_ALL to produce deterministic output.
        """
        mock_style.RESET_ALL = "<RESET>"
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

    @unittest.mock.patch(
        "cli.__main__.subprocess.run", side_effect=Exception("mocked error")
    )
    def test_extract_description_via_help_returns_dash_on_exception(self, mock_run):
        """
        extract_description_via_help() should return '-' if subprocess.run
        raises any exception.
        """
        result = main.extract_description_via_help("/fake/path/script.py")
        self.assertEqual(result, "-")

    @unittest.mock.patch("cli.__main__.subprocess.run")
    def test_show_full_help_for_all_invokes_help_for_each_command(self, mock_run):
        """
        show_full_help_for_all() should execute a help subprocess call for each
        discovered CLI command. The module path must be correct.
        """
        available = [
            (None, "deploy"),
            ("setup", "users"),
        ]

        main.show_full_help_for_all("/fake/cli", available)

        expected_modules = {"cli.deploy", "cli.setup.users"}
        invoked_modules = set()

        for call in mock_run.call_args_list:
            args, kwargs = call
            cmd = args[0]

            # Validate invocation structure
            self.assertGreaterEqual(len(cmd), 3)
            self.assertEqual(cmd[1], "-m")  # Second argument must be '-m'
            invoked_modules.add(cmd[2])  # Module name

            # Validate flags
            self.assertEqual(kwargs.get("capture_output"), True)
            self.assertEqual(kwargs.get("text"), True)
            self.assertEqual(kwargs.get("check"), False)

        self.assertEqual(expected_modules, invoked_modules)

    def test_format_command_help_basic(self):
        name = "cmd"
        description = "A basic description"
        output = main.format_command_help(
            name, description, indent=2, col_width=20, width=40
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
            self.assertEqual([(None, "one"), (None, "two")], commands)

    def test_git_clean_repo_invokes_git_clean(self):
        with unittest.mock.patch("cli.__main__.subprocess.run") as mock_run:
            main.git_clean_repo()
            mock_run.assert_called_once_with(["git", "clean", "-Xfd"], check=True)

    @unittest.mock.patch("cli.__main__.subprocess.run")
    def test_extract_description_via_help_with_description(self, mock_run):
        # Simulate subprocess returning help output with a description
        mock_stdout = "usage: dummy.py [options]\n\nThis is a help description.\n"
        mock_run.return_value = unittest.mock.Mock(stdout=mock_stdout)
        description = main.extract_description_via_help("/fake/path/dummy.py")
        self.assertEqual(description, "This is a help description.")

    @unittest.mock.patch("cli.__main__.subprocess.run")
    def test_extract_description_via_help_without_description(self, mock_run):
        # Simulate subprocess returning help output without a description
        mock_stdout = "usage: empty.py [options]\n"
        mock_run.return_value = unittest.mock.Mock(stdout=mock_stdout)
        description = main.extract_description_via_help("/fake/path/empty.py")
        self.assertEqual(description, "-")

    @unittest.mock.patch("cli.__main__.extract_description_via_help")
    @unittest.mock.patch("cli.__main__.format_command_help")
    @unittest.mock.patch("builtins.print")
    def test_print_global_help_uses_helpers_per_command(
        self, mock_print, mock_fmt, mock_extract
    ):
        """
        print_global_help() should call extract_description_via_help() and
        format_command_help() once per available command, with correct paths.
        """
        cli_dir = "/tmp/cli"
        available = [
            (None, "rootcmd"),
            ("meta/j2", "compiler"),
        ]

        mock_extract.return_value = "DESC"
        mock_fmt.side_effect = lambda name, desc, **kwargs: f"{name}:{desc}"

        main.print_global_help(available, cli_dir)

        # extract_description_via_help should be called with the correct .py paths
        expected_paths = [
            os.path.join(cli_dir, "rootcmd.py"),
            os.path.join(cli_dir, "meta", "j2", "compiler.py"),
        ]
        called_paths = [call.args[0] for call in mock_extract.call_args_list]
        self.assertEqual(expected_paths, called_paths)

        # format_command_help should be called for both commands, in order
        called_names = [call.args[0] for call in mock_fmt.call_args_list]
        self.assertEqual(["rootcmd", "compiler"], called_names)

    @unittest.mock.patch("builtins.print")
    def test__play_in_child_failure_returns_false_and_prints_warning(self, mock_print):
        """
        _play_in_child() should return False and print a diagnostic
        when the child exitcode is non-zero.
        """

        class FakeProcess:
            def __init__(self, target=None, args=None):
                self.exitcode = 1

            def start(self):
                pass

            def join(self):
                pass

        with unittest.mock.patch("cli.__main__.Process", FakeProcess):
            ok = main._play_in_child("play_warning_sound")

        self.assertFalse(ok)
        self.assertTrue(
            any("[sound] child" in str(c.args[0]) for c in mock_print.call_args_list),
            "Expected a diagnostic print when exitcode != 0",
        )

    @unittest.mock.patch("cli.__main__._play_in_child")
    @unittest.mock.patch("cli.__main__.time.sleep")
    def test_failure_with_warning_loop_no_signal_skips_sounds_and_exits(
        self, mock_sleep, mock_play
    ):
        """
        When no_signal=True, failure_with_warning_loop() should not call
        _play_in_child at all and should exit after the timeout.
        """

        # Simulate time.monotonic jumping past the timeout immediately
        with unittest.mock.patch(
            "cli.__main__.time.monotonic", side_effect=[0.0, 100.0]
        ):
            with unittest.mock.patch(
                "cli.__main__.sys.exit", side_effect=SystemExit
            ) as mock_exit:
                with self.assertRaises(SystemExit):
                    main.failure_with_warning_loop(
                        no_signal=True, sound_enabled=True, alarm_timeout=1
                    )

        mock_play.assert_not_called()
        mock_exit.assert_called()  # ensure we attempted to exit


if __name__ == "__main__":
    unittest.main()
