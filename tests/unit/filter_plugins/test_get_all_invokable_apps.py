# tests/unit/filter_plugins/test_get_all_invokable_apps.py
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from unittest.mock import patch

from filter_plugins.get_all_invokable_apps import get_all_invokable_apps


class TestGetAllInvokableApps(unittest.TestCase):
    def setUp(self):
        """Create a temporary roles/ directory with categories.yml and some example roles."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="invokable_apps_test_"))
        self.roles_dir = self.test_dir / "roles"
        self.roles_dir.mkdir(parents=True, exist_ok=True)
        self.categories_file = self.roles_dir / "categories.yml"

        # Write a categories.yml with nested invokable/non-invokable paths
        categories = {
            "roles": {
                "web": {
                    "title": "Web",
                    "invokable": False,
                    "app": {"title": "Applications", "invokable": True},
                    "svc": {"title": "Services", "invokable": False},
                },
                "update": {"title": "Update", "invokable": True},
                "util": {
                    "title": "module_utils",
                    "invokable": False,
                    "desk": {"title": "Desktop module_utils", "invokable": True},
                },
            }
        }
        with self.categories_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(categories, f)

        # Create roles: some should match invokable paths, some shouldn't
        roles = [
            ("web-app-nextcloud", "web-app-nextcloud"),
            ("web-app-matomo", "matomo-app"),  # application_id differs
            ("web-svc-nginx", None),  # should NOT match any invokable path
            ("update", None),  # exact match to invokable path
        ]
        for rolename, appid in roles:
            role_dir = self.roles_dir / rolename
            (role_dir / "vars").mkdir(parents=True, exist_ok=True)
            vars_path = role_dir / "vars" / "main.yml"
            data = {}
            if appid:
                data["application_id"] = appid
            with vars_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

    def tearDown(self):
        """Clean up the temporary test directory after each test."""
        shutil.rmtree(self.test_dir)

    def test_get_all_invokable_apps(self):
        """Should return only applications whose role paths match invokable paths."""
        with patch("module_utils.invokable._repo_root", return_value=self.test_dir):
            result = get_all_invokable_apps()

        expected = sorted(
            [
                "web-app-nextcloud",  # application_id from role
                "matomo-app",  # application_id from role
                "update",  # role directory name
            ]
        )
        self.assertEqual(sorted(result), expected)

    def test_empty_when_no_invokable(self):
        """Should raise RuntimeError if there are no invokable paths in categories.yml."""
        with self.categories_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump({"roles": {"foo": {"invokable": False}}}, f)

        with patch("module_utils.invokable._repo_root", return_value=self.test_dir):
            with self.assertRaises(RuntimeError):
                get_all_invokable_apps()

    def test_empty_when_no_roles(self):
        """Should return an empty list if there are no roles, but categories.yml exists."""
        shutil.rmtree(self.roles_dir)
        self.roles_dir.mkdir(parents=True, exist_ok=True)

        # Recreate categories.yml after removing roles_dir
        with self.categories_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump({"roles": {"web": {"app": {"invokable": True}}}}, f)

        with patch("module_utils.invokable._repo_root", return_value=self.test_dir):
            result = get_all_invokable_apps()

        self.assertEqual(result, [])

    def test_error_when_no_categories_file(self):
        """
        Should raise FileNotFoundError if categories.yml is missing.

        Note: the implementation resolves invokable paths via
        module_utils.invokable._get_invokable_paths().
        To make the test deterministic, patch this function directly.
        """
        self.categories_file.unlink()

        with patch("module_utils.invokable._repo_root", return_value=self.test_dir):
            with patch(
                "module_utils.invokable._get_invokable_paths",
                side_effect=FileNotFoundError,
            ):
                with self.assertRaises(FileNotFoundError):
                    get_all_invokable_apps()


if __name__ == "__main__":
    unittest.main()
