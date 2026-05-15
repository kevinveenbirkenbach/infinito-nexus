import unittest
from pathlib import Path

import yaml

from utils.cache.yaml import load_yaml_any
from utils.roles.mapping import ROLE_FILE_META_SERVICES, ROLE_FILE_VARS_MAIN


class TestDockerRoleServicesConfiguration(unittest.TestCase):
    def test_services_keys_and_templates(self):
        """For each web-app-* role, check that ``meta/services.yml`` contains
        a non-empty mapping at the file root (the services map)."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        roles_dir = repo_root / "roles"
        errors = []
        warnings = []

        for role_path in roles_dir.iterdir():
            if not (role_path.is_dir() and role_path.name.startswith("web-app-")):
                continue

            services_file = role_path / ROLE_FILE_META_SERVICES
            if not services_file.exists():
                continue  # No services manifest to check

            try:
                services = load_yaml_any(services_file) or {}
                main_file = role_path / ROLE_FILE_VARS_MAIN
                load_yaml_any(main_file) or {}
            except yaml.YAMLError as e:
                errors.append(f"{role_path.name}: YAML parse error: {e}")
                continue

            if not services:
                warnings.append(f"[WARNING] {role_path.name}: empty meta/services.yml")
                continue

            if not isinstance(services, dict):
                errors.append(
                    f"{role_path.name}: meta/services.yml file root must be a "
                    "mapping (the services map;)"
                )
                continue
        if warnings:
            print(
                "\nWarnings in docker role services configuration:\n"
                + "\n".join(warnings)
            )
        if errors:
            self.fail(
                "Errors in docker role services configuration:\n" + "\n".join(errors)
            )


if __name__ == "__main__":
    unittest.main()
