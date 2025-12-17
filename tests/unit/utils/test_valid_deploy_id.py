# File: tests/unit/module_utils/test_valid_deploy_id.py
import os
import tempfile
import unittest
import yaml
from module_utils.valid_deploy_id import ValidDeployId


class TestValidDeployId(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for roles
        self.temp_dir = tempfile.TemporaryDirectory()
        self.roles_dir = os.path.join(self.temp_dir.name, "roles")
        os.makedirs(self.roles_dir)

        # Create a dummy role with application_id 'app1'
        role_path = os.path.join(self.roles_dir, "role1", "vars")
        os.makedirs(role_path)
        with open(os.path.join(role_path, "main.yml"), "w", encoding="utf-8") as f:
            yaml.safe_dump({"application_id": "app1"}, f)

        # Initialize validator with our temp roles_dir
        self.validator = ValidDeployId(roles_dir=self.roles_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_ini_inventory(self, content):
        fd, path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _write_yaml_inventory(self, data):
        fd, path = tempfile.mkstemp(suffix=".yml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)
        return path

    def test_valid_in_roles_and_ini_inventory(self):
        # Inventory contains app1 as a host
        ini_content = """
        [servers]
        app1,otherhost
        """
        inv = self._write_ini_inventory(ini_content)
        result = self.validator.validate(inv, ["app1"])
        self.assertEqual(
            result, {}, "app1 should be valid when in roles and ini inventory"
        )

    def test_missing_in_roles(self):
        # Inventory contains app2 but roles only have app1
        ini_content = """
        [servers]
        app2
        """
        inv = self._write_ini_inventory(ini_content)
        result = self.validator.validate(inv, ["app2"])
        # app2 not in roles, but in inventory
        expected = {"app2": {"in_roles": False, "in_inventory": True}}
        self.assertEqual(result, expected)

    def test_missing_in_inventory_ini(self):
        # Roles have app1 but inventory does not mention it
        ini_content = """
        [servers]
        otherhost
        """
        inv = self._write_ini_inventory(ini_content)
        result = self.validator.validate(inv, ["app1"])
        expected = {"app1": {"in_roles": True, "in_inventory": False}}
        self.assertEqual(result, expected)

    def test_missing_both_ini(self):
        # Neither roles nor inventory have appX
        ini_content = """
        [servers]
        otherhost
        """
        inv = self._write_ini_inventory(ini_content)
        result = self.validator.validate(inv, ["appX"])
        expected = {"appX": {"in_roles": False, "in_inventory": False}}
        self.assertEqual(result, expected)

    def test_valid_in_roles_and_yaml_inventory(self):
        # YAML inventory with app1 as a dict key
        data = {"app1": {"hosts": ["app1"]}, "group": {"app1": {}}}
        inv = self._write_yaml_inventory(data)
        result = self.validator.validate(inv, ["app1"])
        self.assertEqual(result, {}, "app1 should be valid in roles and yaml inventory")

    def test_missing_in_roles_yaml(self):
        # YAML inventory has app2 key but roles only have app1
        data = {"app2": {}}
        inv = self._write_yaml_inventory(data)
        result = self.validator.validate(inv, ["app2"])
        expected = {"app2": {"in_roles": False, "in_inventory": True}}
        self.assertEqual(result, expected)

    def test_missing_in_inventory_yaml(self):
        # Roles have app1 but YAML inventory has no app1
        data = {"group": {"other": {}}}
        inv = self._write_yaml_inventory(data)
        result = self.validator.validate(inv, ["app1"])
        expected = {"app1": {"in_roles": True, "in_inventory": False}}
        self.assertEqual(result, expected)

    def test_missing_both_yaml(self):
        data = {}
        inv = self._write_yaml_inventory(data)
        result = self.validator.validate(inv, ["unknown"])
        expected = {"unknown": {"in_roles": False, "in_inventory": False}}
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
