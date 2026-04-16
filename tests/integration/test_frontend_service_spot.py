import unittest
from pathlib import Path

from utils.service_registry import (
    build_service_registry_from_roles_dir,
    load_applications_from_roles_dir,
    ordered_primary_service_entries,
)


class TestFrontendServiceSpot(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.roles_dir = self.repo_root / "roles"
        self.applications = load_applications_from_roles_dir(self.roles_dir)
        self.service_registry = build_service_registry_from_roles_dir(self.roles_dir)
        self.ordered = ordered_primary_service_entries(
            self.service_registry,
            self.roles_dir,
        )

    def _index(self, role_name: str) -> int:
        for index, entry in enumerate(self.ordered):
            if entry["role"] == role_name:
                return index
        self.fail(f"Role {role_name} not found in ordered service registry")

    def test_bucket_order_is_monotonic(self):
        bucket_order = {
            "universal": 0,
            "workstation": 1,
            "server": 2,
            "web-svc": 3,
            "web-app": 4,
        }
        actual = [bucket_order[entry["bucket"]] for entry in self.ordered]
        self.assertEqual(actual, sorted(actual))

    def test_dashboard_is_loaded_after_matomo(self):
        self.assertLess(self._index("web-app-matomo"), self._index("web-app-dashboard"))

    def test_keycloak_respects_run_after_dependencies(self):
        self.assertLess(self._index("web-app-matomo"), self._index("web-app-keycloak"))
        self.assertLess(self._index("web-app-mailu"), self._index("web-app-keycloak"))


if __name__ == "__main__":
    unittest.main()
