import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestStrongPasswordFilterPathIntegration(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ansible"), "ansible not found")
    def test_strong_password_filter_uses_repo_relative_utils_path(self):
        repo_root = Path(__file__).resolve().parents[2]
        source_plugin = repo_root / "plugins" / "filter" / "value_generator.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "filter_plugins"
            plugins_dir.mkdir()
            (plugins_dir / "value_generator.py").symlink_to(source_plugin)

            env = os.environ.copy()
            env["ANSIBLE_FILTER_PLUGINS"] = str(plugins_dir)
            env["ANSIBLE_LOCAL_TEMP"] = "/tmp/ansible-local"
            env["ANSIBLE_REMOTE_TEMP"] = "/tmp/ansible-remote"

            result = subprocess.run(
                [
                    "ansible",
                    "localhost",
                    "-i",
                    "localhost,",
                    "-c",
                    "local",
                    "-m",
                    "ansible.builtin.debug",
                    "-a",
                    "msg={{ 16 | strong_password }}",
                ],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
            )

        combined_output = f"{result.stdout}\n{result.stderr}"

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "strong_password filter failed to load via ansible\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            ),
        )
        self.assertIn("msg:", combined_output)
        self.assertNotIn("plugins/utils", combined_output)


if __name__ == "__main__":
    unittest.main()
