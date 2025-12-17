import os
import shutil
import tempfile
import yaml
import unittest

from filter_plugins.get_all_invokable_apps import get_all_invokable_apps


class TestGetAllInvokableApps(unittest.TestCase):
    def setUp(self):
        """Create a temporary roles/ directory with categories.yml and some example roles."""
        self.test_dir = tempfile.mkdtemp(prefix="invokable_apps_test_")
        self.roles_dir = os.path.join(self.test_dir, "roles")
        os.makedirs(self.roles_dir, exist_ok=True)
        self.categories_file = os.path.join(self.roles_dir, "categories.yml")

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
        with open(self.categories_file, "w") as f:
            yaml.safe_dump(categories, f)

        # Create roles: some should match invokable paths, some shouldn't
        roles = [
            ("web-app-nextcloud", "web-app-nextcloud"),
            ("web-app-matomo", "matomo-app"),  # application_id differs
            ("web-svc-nginx", None),  # should NOT match any invokable path
            ("update", None),  # exact match to invokable path
            ("util-desk-custom", None),  # matches util-desk
        ]
        for rolename, appid in roles:
            role_dir = os.path.join(self.roles_dir, rolename)
            os.makedirs(os.path.join(role_dir, "vars"), exist_ok=True)
            vars_path = os.path.join(role_dir, "vars", "main.yml")
            data = {}
            if appid:
                data["application_id"] = appid
            with open(vars_path, "w") as f:
                yaml.safe_dump(data, f)

    def tearDown(self):
        """Clean up the temporary test directory after each test."""
        shutil.rmtree(self.test_dir)

    def test_get_all_invokable_apps(self):
        """Should return only applications whose role paths match invokable paths."""
        result = get_all_invokable_apps(
            categories_file=self.categories_file, roles_dir=self.roles_dir
        )
        expected = sorted(
            [
                "web-app-nextcloud",  # application_id from role
                "matomo-app",  # application_id from role
                "update",  # role directory name
                "util-desk-custom",  # role directory name
            ]
        )
        self.assertEqual(sorted(result), expected)

    def test_empty_when_no_invokable(self):
        """Should return an empty list if there are no invokable paths in categories.yml."""
        with open(self.categories_file, "w") as f:
            yaml.safe_dump({"roles": {"foo": {"invokable": False}}}, f)
        result = get_all_invokable_apps(
            categories_file=self.categories_file, roles_dir=self.roles_dir
        )
        self.assertEqual(result, [])

    def test_empty_when_no_roles(self):
        """Should return an empty list if there are no roles, but categories.yml exists."""
        shutil.rmtree(self.roles_dir)
        os.makedirs(self.roles_dir, exist_ok=True)
        # Recreate categories.yml after removing roles_dir
        with open(self.categories_file, "w") as f:
            yaml.safe_dump({"roles": {"web": {"app": {"invokable": True}}}}, f)
        result = get_all_invokable_apps(
            categories_file=self.categories_file, roles_dir=self.roles_dir
        )
        self.assertEqual(result, [])

    def test_error_when_no_categories_file(self):
        """Should raise FileNotFoundError if categories.yml is missing."""
        os.remove(self.categories_file)
        with self.assertRaises(FileNotFoundError):
            get_all_invokable_apps(
                categories_file=self.categories_file, roles_dir=self.roles_dir
            )


if __name__ == "__main__":
    unittest.main()
