import unittest
import os
import sys
import subprocess


class CLIHelpIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        cls.cli_dir = os.path.join(cls.project_root, "cli")
        cls.main_py = os.path.join(cls.cli_dir, "__main__.py")
        cls.python = sys.executable

    def test_all_cli_commands_help(self):
        """
        Iteriere über alle .py Dateien in cli/, baue daraus die
        Subcommand-Pfade und prüfe, dass `python main.py <cmd> --help`
        mit Exit-Code 0 endet.
        """
        for root, _, files in os.walk(self.cli_dir):
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue

                rel_dir = os.path.relpath(root, self.cli_dir)
                cmd_name = os.path.splitext(fname)[0]
                if rel_dir == ".":
                    segments = [cmd_name]
                else:
                    segments = rel_dir.split(os.sep) + [cmd_name]

                with self.subTest(command=" ".join(segments)):
                    cmd = (
                        [self.python, self.main_py]
                        + segments
                        + ["--help", "--no-signal"]
                    )
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=(
                            f"Command `{' '.join(cmd)}` failed\n"
                            f"stdout:\n{result.stdout}\n"
                            f"stderr:\n{result.stderr}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
