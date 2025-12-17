import os
import tempfile
import unittest
import yaml
from pathlib import Path

from filter_plugins.get_app_conf import (
    get_app_conf,
    AppConfigKeyError,
    ConfigEntryNotSetError,
)


class TestGetAppConfFunctionality(unittest.TestCase):
    def setUp(self):
        # Create a temp directory to simulate roles and schema files
        self.tempdir = tempfile.TemporaryDirectory()
        self.roles_dir = Path(self.tempdir.name) / "roles"
        self.roles_dir.mkdir()

        # application_id used in tests
        self.app_id = "testapp"
        # application dict missing the 'nested.key'
        self.applications = {self.app_id: {}}

        # Create schema directory and file for testapp
        schema_dir = self.roles_dir / self.app_id / "schema"
        schema_dir.mkdir(parents=True)
        schema_file = schema_dir / "main.yml"
        # Define a nested key in schema
        schema_data = {"nested": {"key": ""}}
        with schema_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(schema_data, f)

        # Change cwd so get_app_conf finds roles/<app_id>/schema/main.yml
        self.orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tempdir.cleanup()

    def test_config_entry_not_set_error_raised(self):
        # Attempt to access a key defined in schema but not set in applications
        with self.assertRaises(ConfigEntryNotSetError):
            get_app_conf(self.applications, self.app_id, "nested.key", strict=True)

    def test_strict_key_error_when_not_in_schema(self):
        # Access a key not defined in schema nor in applications
        with self.assertRaises(AppConfigKeyError):
            get_app_conf(self.applications, self.app_id, "undefined.path", strict=True)

    def test_non_strict_returns_default(self):
        # Non-strict mode should return default instead of raising
        default_val = "fallback"
        result = get_app_conf(
            self.applications,
            self.app_id,
            "nested.key",
            strict=False,
            default=default_val,
        )
        self.assertEqual(result, default_val)

    def test_list_indexing_and_missing(self):
        # Extend schema to define a list
        schema_file = Path("roles") / self.app_id / "schema" / "main.yml"
        schema_data = {"items": [""]}
        with schema_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(schema_data, f)

        # Insert list into applications but leave index out of range
        self.applications[self.app_id]["items"] = []
        with self.assertRaises(AppConfigKeyError):
            get_app_conf(self.applications, self.app_id, "items[0]", strict=True)


if __name__ == "__main__":
    unittest.main()
