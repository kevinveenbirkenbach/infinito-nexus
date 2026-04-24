import unittest
import tempfile
import shutil
import os
from pathlib import Path
import subprocess
import sys
import yaml

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../../../cli/validate/inventory/__main__.py"
    )
)


class TestValidateInventory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.roles_dir = Path(self.temp_dir) / "roles"
        (self.roles_dir / "app1" / "config").mkdir(parents=True)
        (self.roles_dir / "identity" / "users").mkdir(parents=True)
        self.inventory_dir = Path(self.temp_dir) / "inventory"
        self.inventory_dir.mkdir()

        (self.roles_dir / "app1" / "config" / "main.yml").write_text(
            yaml.safe_dump(
                {"port": 8080, "enabled": True, "settings": {"theme": "dark"}}
            ),
            encoding="utf-8",
        )
        (self.roles_dir / "identity" / "users" / "main.yml").write_text(
            yaml.safe_dump({"users": {"alice": {"email": "alice@example.com"}}}),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def run_script(self, expected_code=0):
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT_PATH,
                str(self.inventory_dir),
                "--roles-dir",
                str(self.roles_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            cwd=self.temp_dir,
        )
        if result.returncode != expected_code:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        return result

    def test_valid_inventory(self):
        (self.inventory_dir / "group_vars.yml").write_text(
            yaml.dump(
                {
                    "applications": {
                        "app1": {
                            "port": 8080,
                            "enabled": True,
                            "settings": {"theme": "dark"},
                        }
                    },
                    "users": {
                        "alice": {
                            "email": "alice@example.com",
                            "password": "secret",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        result = self.run_script(expected_code=0)
        self.assertIn("Inventory directory is valid against defaults", result.stdout)

    def test_unknown_user_warning(self):
        (self.inventory_dir / "invalid_users.yml").write_text(
            yaml.dump({"users": {"bob": {"email": "bob@example.com"}}}),
            encoding="utf-8",
        )

        result = self.run_script(expected_code=0)
        self.assertIn("Warning", result.stderr)

    def test_missing_user_key_fails(self):
        (self.inventory_dir / "invalid_key.yml").write_text(
            yaml.dump(
                {
                    "users": {
                        "alice": {
                            "email": "alice@example.com",
                            "extra": "unexpected",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        result = self.run_script(expected_code=1)
        self.assertIn("Missing default for user 'alice': key 'extra'", result.stderr)

    def test_missing_application_key_fails(self):
        (self.inventory_dir / "missing_key.yml").write_text(
            yaml.dump(
                {
                    "applications": {
                        "app1": {
                            "port": 8080,
                            "enabled": True,
                            "settings": {"theme": "dark"},
                            "extra_setting": True,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        result = self.run_script(expected_code=1)
        self.assertIn("Missing default for app1: extra_setting", result.stdout)


if __name__ == "__main__":
    unittest.main()
