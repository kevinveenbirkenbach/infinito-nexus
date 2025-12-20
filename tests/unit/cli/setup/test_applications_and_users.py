import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
import subprocess


class TestGenerateDefaultApplicationsUsers(unittest.TestCase):
    def setUp(self):
        # Setup temporary roles directory
        self.temp_dir = Path(tempfile.mkdtemp())
        self.roles_dir = self.temp_dir / "roles"
        self.roles_dir.mkdir()

        # Sample role with users meta
        self.role = self.roles_dir / "web-app-app-with-users"
        (self.role / "vars").mkdir(parents=True)
        (self.role / "config").mkdir(parents=True)
        (self.role / "meta").mkdir(parents=True)
        (self.role / "users").mkdir(parents=True)

        # Write application_id and configuration
        (self.role / "vars" / "main.yml").write_text("application_id: app_with_users\n")
        (self.role / "config" / "main.yml").write_text("setting: value\n")

        # Write users meta
        users_meta = {
            "users": {
                "alice": {"uid": 2001, "gid": 2001},
                "bob": {"uid": 2002, "gid": 2002},
            }
        }
        with (self.role / "users" / "main.yml").open("w", encoding="utf-8") as f:
            yaml.dump(users_meta, f)

        # Output file path
        self.output_file = self.temp_dir / "output.yml"

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_users_injection(self):
        """
        When a users.yml exists with defined users, the script should inject a 'users'
        mapping in the generated YAML, mapping each username to a Jinja2 reference.
        """
        script_path = (
            Path(__file__).resolve().parents[4] / "cli" / "setup/applications/__main__.py"
        )
        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = yaml.safe_load(self.output_file.read_text())

        apps = data.get("defaults_applications", {})
        # Only the app with users should be present
        self.assertIn("app_with_users", apps)

        # 'users' section should be present and correct
        users_map = apps["app_with_users"]["users"]
        expected = {"alice": '{{ users["alice"] }}', "bob": '{{ users["bob"] }}'}
        self.assertEqual(users_map, expected)


if __name__ == "__main__":
    unittest.main()
