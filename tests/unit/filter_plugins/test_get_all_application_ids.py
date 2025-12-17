import unittest
import tempfile
import os
import yaml

from filter_plugins.get_all_application_ids import get_all_application_ids


class TestGetAllApplicationIds(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to act as the roles base
        self.tmpdir = tempfile.TemporaryDirectory()
        self.roles_dir = os.path.join(self.tmpdir.name, "roles")
        os.makedirs(self.roles_dir)

    def tearDown(self):
        # Clean up temporary directory
        self.tmpdir.cleanup()

    def create_role(self, role_name, data):
        # Helper to create roles/<role_name>/vars/main.yml with given dict
        path = os.path.join(self.roles_dir, role_name, "vars")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "main.yml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def test_single_application_id(self):
        self.create_role("role1", {"application_id": "app1"})
        result = get_all_application_ids(self.roles_dir)
        self.assertEqual(result, ["app1"])

    def test_multiple_application_ids(self):
        self.create_role("role1", {"application_id": "app1"})
        self.create_role("role2", {"application_id": "app2"})
        result = get_all_application_ids(self.roles_dir)
        self.assertEqual(sorted(result), ["app1", "app2"])

    def test_duplicate_application_ids(self):
        self.create_role("role1", {"application_id": "app1"})
        self.create_role("role2", {"application_id": "app1"})
        result = get_all_application_ids(self.roles_dir)
        self.assertEqual(result, ["app1"])

    def test_missing_application_id(self):
        self.create_role("role1", {"other_key": "value"})
        result = get_all_application_ids(self.roles_dir)
        self.assertEqual(result, [])

    def test_no_roles_directory(self):
        # Point to a non-existent directory
        empty_dir = os.path.join(self.tmpdir.name, "no_roles_here")
        result = get_all_application_ids(empty_dir)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
