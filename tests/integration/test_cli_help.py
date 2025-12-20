import os
import sys
import subprocess
import unittest


class CLIHelpIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        cls.cli_dir = os.path.join(cls.project_root, "cli")
        cls.main_py = os.path.join(cls.cli_dir, "__main__.py")
        cls.python = sys.executable

    def _discover_command_dirs(self):
        """
        Discover commands as package directories under cli/ that contain __main__.py.

        Rules:
          - cli/<...>/__main__.py marks a command package
          - cli/__main__.py is the dispatcher, not a command
          - ignore __pycache__
        Returns:
          list[list[str]] command segments, e.g. ["deploy","container"]
        """
        commands = []
        for root, dirnames, filenames in os.walk(self.cli_dir):
            # Prune __pycache__
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]

            if "__main__.py" not in filenames:
                continue

            rel_dir = os.path.relpath(root, self.cli_dir)
            if rel_dir == ".":
                # cli/__main__.py is the dispatcher, not a command
                continue

            segments = rel_dir.split(os.sep)
            commands.append(segments)

        # stable order for test output
        commands.sort(key=lambda s: "/".join(s))
        return commands

    def test_all_cli_commands_help(self):
        for segments in self._discover_command_dirs():
            with self.subTest(command=" ".join(segments)):
                cmd = [self.python, self.main_py] + segments + ["--help", "--no-signal"]
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
