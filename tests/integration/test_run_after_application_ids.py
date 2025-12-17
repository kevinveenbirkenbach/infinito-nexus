#!/usr/bin/env python3
import unittest
import yaml
from pathlib import Path


class TestRunAfterRoles(unittest.TestCase):
    def setUp(self):
        self.roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        self.valid_role_names = {p.name for p in self.roles_dir.iterdir() if p.is_dir()}

    def test_run_after_roles_are_valid(self):
        invalid_refs = []

        for role in self.valid_role_names:
            meta_path = self.roles_dir / role / "meta" / "main.yml"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                self.fail(f"Failed to parse {meta_path}: {e}")
                continue

            run_after = data.get("galaxy_info", {}).get("run_after", [])
            for ref in run_after:
                if ref not in self.valid_role_names:
                    invalid_refs.append((role, ref))

        if invalid_refs:
            msg = "\n".join(
                f"{role}: invalid run_after → {ref}" for role, ref in invalid_refs
            )
            self.fail(f"Found invalid run_after references:\n{msg}")


if __name__ == "__main__":
    unittest.main()
