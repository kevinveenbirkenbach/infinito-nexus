import os
import unittest

import yaml

from plugins.lookup.service import LookupModule


class TestServiceTransitiveDependencies(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        service_registry_file = os.path.join(
            self.repo_root, "group_vars", "all", "20_services.yml"
        )
        with open(service_registry_file, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        self.service_registry = data.get("SERVICE_REGISTRY", {})

        self.applications = {
            "web-app-dashboard": self._load_yaml(
                "roles", "web-app-dashboard", "config", "main.yml"
            ),
            "web-svc-asset": self._load_yaml(
                "roles", "web-svc-asset", "config", "main.yml"
            ),
            "web-svc-file": self._load_yaml(
                "roles", "web-svc-file", "config", "main.yml"
            ),
        }

    def _load_yaml(self, *parts):
        path = os.path.join(self.repo_root, *parts)
        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def test_dashboard_needs_file_transitively_via_asset_service(self):
        result = LookupModule().run(
            ["file"],
            variables={
                "applications": self.applications,
                "group_names": ["web-app-dashboard"],
                "SERVICE_REGISTRY": self.service_registry,
            },
        )[0]

        self.assertTrue(result["needed"])
        self.assertEqual(result["id"], "file")
        self.assertEqual(result["role"], "web-svc-file")


if __name__ == "__main__":
    unittest.main()
