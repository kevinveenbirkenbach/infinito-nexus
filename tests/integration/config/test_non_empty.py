import glob
import unittest
from pathlib import Path

import yaml

from . import PROJECT_ROOT


def find_none_values(data, prefix=None):
    """
    Recursively find keys with None values in a nested dict or list.
    Returns a list of (path, value) tuples where value is None.
    """
    errors = []
    if prefix is None:
        prefix = []

    if isinstance(data, dict):
        for key, value in data.items():
            path = [*prefix, str(key)]
            if value is None:
                errors.append((".".join(path), value))
            elif isinstance(value, (dict, list)):
                errors.extend(find_none_values(value, path))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            path = [*prefix, f"[{idx}]"]
            if item is None:
                errors.append((".".join(path), item))
            elif isinstance(item, (dict, list)):
                errors.extend(find_none_values(item, path))

    return errors


class TestConfigurationNoNone(unittest.TestCase):
    def test_configuration_files_have_no_none_values(self):
        # Post-req-008: per-role configuration lives in roles/*/meta/*.yml
        # (services.yml, server.yml, rbac.yml, schema.yml, users.yml,
        # volumes.yml). The legacy roles/*/config/main.yml file no longer
        # exists. Recurse into every meta/*.yml file and assert no key
        # resolves to a YAML null.
        roles_root = str(PROJECT_ROOT / "roles")
        pattern = str(Path(roles_root) / "*" / "meta" / "*.yml")
        files = glob.glob(pattern)
        self.assertTrue(
            files, f"No roles/*/meta/*.yml files found with pattern: {pattern}"
        )

        all_errors = []
        for filepath in files:
            with Path(filepath).open() as f:
                try:
                    data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    self.fail(f"Failed to parse YAML in {filepath}: {e}")
            errors = find_none_values(data)
            for path, _value in errors:
                all_errors.append(f"{filepath}: Key '{path}' is None")

        if all_errors:
            self.fail(
                "None values found in configuration files:\n" + "\n".join(all_errors)
            )


if __name__ == "__main__":
    unittest.main()
