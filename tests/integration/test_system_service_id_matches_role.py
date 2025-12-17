#!/usr/bin/env python3
import os
import glob
import unittest
import yaml


class TestSystemServiceIdMatchesRole(unittest.TestCase):
    def setUp(self):
        # Repo root = three levels up from this file: tests/integration/<this_file>.py
        self.repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.roles_dir = os.path.join(self.repo_root, "roles")
        self.assertTrue(
            os.path.isdir(self.roles_dir),
            f"'roles' directory not found at: {self.roles_dir}",
        )

    def _load_yaml(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def test_system_service_id_equals_role_name(self):
        role_dirs = [
            d
            for d in os.listdir(self.roles_dir)
            if os.path.isdir(os.path.join(self.roles_dir, d))
        ]

        self.assertGreater(
            len(role_dirs), 0, f"No role directories found in {self.roles_dir}"
        )

        for role in sorted(role_dirs):
            with self.subTest(role=role):
                vars_dir = os.path.join(self.roles_dir, role, "vars")
                if not os.path.isdir(vars_dir):
                    continue

                candidates = []
                candidates.extend(glob.glob(os.path.join(vars_dir, "main.yml")))
                candidates.extend(glob.glob(os.path.join(vars_dir, "main.yaml")))
                if not candidates:
                    continue

                vars_file = sorted(
                    candidates, key=lambda p: (not p.endswith("main.yml"), p)
                )[0]
                data = self._load_yaml(vars_file)

                if "system_service_id" not in (data or {}):
                    continue

                value = str(data.get("system_service_id")).strip()
                allowed = {role, role + "@", "{{ application_id }}"}

                self.assertIn(
                    value,
                    allowed,
                    (
                        f"[{role}] system_service_id mismatch in {vars_file}.\n"
                        f"  Allowed: {sorted(allowed)}\n"
                        f"  Actual:  {value}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
