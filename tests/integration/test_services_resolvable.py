import os
import unittest
import yaml

from plugins.lookup.service import LookupModule


class TestServicesResolvable(unittest.TestCase):
    """Every entry in group_vars/all/20_services.yml must be resolvable
    via the service lookup plugin both by service key and by role name."""

    def setUp(self):
        self.repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        services_file = os.path.join(
            self.repo_root, "group_vars", "all", "20_services.yml"
        )
        with open(services_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.service_registry = data.get("SERVICE_REGISTRY", {})
        self.assertGreater(
            len(self.service_registry), 0, "service registry must not be empty"
        )

    def _run(self, term):
        return LookupModule().run(
            [term],
            variables={
                "applications": {},
                "group_names": [],
                "SERVICE_REGISTRY": self.service_registry,
            },
        )[0]

    def _canonical_for(self, key):
        entry = self.service_registry[key]
        return entry.get("canonical", key)

    def test_all_keys_resolvable(self):
        """Every service key must resolve without error and return itself as id."""
        for key in self.service_registry:
            with self.subTest(key=key):
                result = self._run(key)
                self.assertEqual(result["id"], key)

    def test_all_roles_resolve_to_canonical(self):
        """Role-based lookup must return the canonical key for that role."""
        seen_roles = set()
        for key, entry in self.service_registry.items():
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            if not role or role in seen_roles:
                continue
            seen_roles.add(role)
            canonical = self._canonical_for(key)
            with self.subTest(role=role, expected_canonical=canonical):
                result = self._run(role)
                self.assertEqual(result["role"], role)
                self.assertEqual(result["id"], canonical)

    def test_key_and_role_produce_identical_result_for_primary_keys(self):
        """For the canonical/primary key of a role, key and role lookups must agree."""
        for key, entry in self.service_registry.items():
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            if not role:
                continue
            # Only test primary keys (no canonical field = this key IS canonical)
            if "canonical" in entry:
                continue
            with self.subTest(key=key):
                by_key = self._run(key)
                by_role = self._run(role)
                self.assertEqual(by_key, by_role)


if __name__ == "__main__":
    unittest.main()
