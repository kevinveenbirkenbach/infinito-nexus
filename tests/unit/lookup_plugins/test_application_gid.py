import os
import sys
import tempfile
import shutil
import unittest
import yaml
from lookup_plugins.application_gid import LookupModule

class TestApplicationGidLookup(unittest.TestCase):

    def setUp(self):
        # Create a temporary roles directory
        self.temp_dir = tempfile.mkdtemp()
        self.roles_dir = os.path.join(self.temp_dir, "roles")
        os.mkdir(self.roles_dir)

        # Define mock application_ids
        self.applications = {
            "nextcloud": "web-app-nextcloud",
            "moodle": "web-app-moodle",
            "wordpress": "web-app-wordpress",
            "taiga": "web-app-taiga"
        }

        # Create fake role dirs and vars/main.yml
        for app_id, dirname in self.applications.items():
            role_path = os.path.join(self.roles_dir, dirname, "vars")
            os.makedirs(role_path)
            with open(os.path.join(role_path, "main.yml"), "w") as f:
                yaml.dump({"application_id": app_id}, f)

        self.lookup = LookupModule()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_gid_lookup(self):
        # The sorted application_ids: [moodle, nextcloud, taiga, wordpress]
        expected_order = ["moodle", "nextcloud", "taiga", "wordpress"]
        for i, app_id in enumerate(expected_order):
            result = self.lookup.run([app_id], roles_dir=self.roles_dir)
            self.assertEqual(result, [10000 + i])

    def test_custom_base_gid(self):
        result = self.lookup.run(["taiga"], roles_dir=self.roles_dir, base_gid=20000)
        self.assertEqual(result, [20002])  # 2nd index in sorted list

    def test_application_id_not_found(self):
        with self.assertRaises(Exception) as context:
            self.lookup.run(["unknownapp"], roles_dir=self.roles_dir)
        self.assertIn("Application ID 'unknownapp' not found", str(context.exception))


if __name__ == '__main__':
    unittest.main()
