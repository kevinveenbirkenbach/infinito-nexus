import os
import unittest
import yaml
from collections import defaultdict


class TestServicesCanonical(unittest.TestCase):
    """Lint: canonical field in group_vars/all/20_services.yml must be consistent.

    Rules:
    - If a role is shared by multiple keys, all alias keys MUST declare canonical.
    - canonical must point to an existing key in the services map.
    - The canonical target must share the same role as the alias.
    - The canonical target must NOT itself have a canonical field (no chaining).
    - Exactly one key per role must be the primary (no canonical field).
    """

    def setUp(self):
        self.repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        services_file = os.path.join(
            self.repo_root, "group_vars", "all", "20_services.yml"
        )
        with open(services_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.services = data.get("services", {})
        self.assertGreater(len(self.services), 0, "services map must not be empty")

        # Build role → [keys] index
        self.role_to_keys = defaultdict(list)
        for key, entry in self.services.items():
            if isinstance(entry, dict) and "role" in entry:
                self.role_to_keys[entry["role"]].append(key)

    def test_shared_roles_have_canonical(self):
        """All keys sharing a role (except the primary) must declare canonical."""
        for role, keys in self.role_to_keys.items():
            if len(keys) < 2:
                continue
            primaries = [k for k in keys if "canonical" not in self.services[k]]
            with self.subTest(role=role):
                self.assertEqual(
                    len(primaries),
                    1,
                    f"Role '{role}' is shared by {keys} but has "
                    f"{len(primaries)} primary key(s) (no canonical): {primaries}. "
                    f"Exactly one primary is required.",
                )

    def test_canonical_target_exists(self):
        """canonical must reference an existing service key."""
        for key, entry in self.services.items():
            if not isinstance(entry, dict):
                continue
            canonical = entry.get("canonical")
            if canonical is None:
                continue
            with self.subTest(key=key):
                self.assertIn(
                    canonical,
                    self.services,
                    f"[{key}] canonical: '{canonical}' does not exist in services.",
                )

    def test_canonical_target_has_same_role(self):
        """canonical target must map to the same role as the alias."""
        for key, entry in self.services.items():
            if not isinstance(entry, dict):
                continue
            canonical = entry.get("canonical")
            if canonical is None:
                continue
            with self.subTest(key=key):
                alias_role = entry.get("role")
                target_entry = self.services.get(canonical, {})
                target_role = (
                    target_entry.get("role") if isinstance(target_entry, dict) else None
                )
                self.assertEqual(
                    alias_role,
                    target_role,
                    f"[{key}] canonical: '{canonical}' has role '{target_role}', "
                    f"but alias has role '{alias_role}'. Roles must match.",
                )

    def test_canonical_target_is_not_itself_an_alias(self):
        """canonical must not point to another alias (no chaining)."""
        for key, entry in self.services.items():
            if not isinstance(entry, dict):
                continue
            canonical = entry.get("canonical")
            if canonical is None:
                continue
            with self.subTest(key=key):
                target_entry = self.services.get(canonical, {})
                target_canonical = (
                    target_entry.get("canonical")
                    if isinstance(target_entry, dict)
                    else None
                )
                self.assertIsNone(
                    target_canonical,
                    f"[{key}] canonical: '{canonical}' is itself an alias "
                    f"(canonical: '{target_canonical}'). Chaining is not allowed.",
                )

    def test_unique_roles_must_not_have_canonical(self):
        """A key that is the only key for its role must not declare canonical."""
        for key, entry in self.services.items():
            if not isinstance(entry, dict):
                continue
            canonical = entry.get("canonical")
            if canonical is None:
                continue
            role = entry.get("role")
            if role is None:
                continue
            with self.subTest(key=key):
                siblings = self.role_to_keys.get(role, [])
                self.assertGreater(
                    len(siblings),
                    1,
                    f"[{key}] declares canonical: '{canonical}' but is the only "
                    f"key for role '{role}'. canonical is only needed for shared roles.",
                )


if __name__ == "__main__":
    unittest.main()
