import os
import re
import yaml
import tempfile
import shutil
import unittest

# Module under test
import cli.validate.inventory as inventory_mod


class TestValidateHostKeys(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.valid_ids = {"valid-service", "another-service"}

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def write_devices_yaml(self, groups):
        # Build the YAML structure
        content = {"all": {"children": {}}}
        for group, hosts in groups.items():
            # hosts is a list of hostnames
            content["all"]["children"][group] = {"hosts": {h: None for h in hosts}}
        path = os.path.join(self.test_dir, "devices.yml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(content, f)
        return path

    def test_no_invalid_groups(self):
        # All groups valid
        groups = {"valid-service": ["host1"], "another-service": ["host2", "host3"]}
        self.write_devices_yaml(groups)
        errors = inventory_mod.validate_host_keys(self.valid_ids, self.test_dir)
        self.assertEqual(errors, [], f"Expected no errors, got {errors}")

    def test_single_invalid_group(self):
        # One invalid group
        groups = {"valid-service": ["host1"], "invalid-service": ["host2"]}
        self.write_devices_yaml(groups)
        errors = inventory_mod.validate_host_keys(self.valid_ids, self.test_dir)
        self.assertEqual(len(errors), 1)
        self.assertRegex(
            errors[0], r"Invalid group 'invalid-service'.*not in application_ids"
        )

    def test_multiple_invalid_groups(self):
        # Multiple invalid groups
        groups = {"bad-one": ["h1"], "bad-two": ["h2"], "valid-service": ["h3"]}
        self.write_devices_yaml(groups)
        errors = inventory_mod.validate_host_keys(self.valid_ids, self.test_dir)
        self.assertEqual(len(errors), 2)
        found = {re.search(r"Invalid group '(.+?)'", e).group(1) for e in errors}
        self.assertSetEqual(found, {"bad-one", "bad-two"})


if __name__ == "__main__":
    unittest.main()
