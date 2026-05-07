import glob
import unittest
from pathlib import Path

import yaml

from plugins.filter.invokable_paths import get_invokable_paths


class TestSysRolesApplicationId(unittest.TestCase):
    """
    Integration tests for sys-* roles based on categories.yml prefixes:
    For each actual sys-* directory under roles/:
      - If dash-joined prefix is in invokable_paths -> vars/main.yml must exist and contain application_id.
      - Otherwise (non-invokable or undeclared) -> if vars/main.yml exists, it must NOT contain application_id.
    """

    @classmethod
    def setUpClass(cls):
        from . import PROJECT_ROOT

        cls.base_dir = str(PROJECT_ROOT)
        cat_file = str(PROJECT_ROOT / "roles" / "categories.yml")
        cls.invokable_prefixes = set(get_invokable_paths(cat_file))
        # collect actual sys dirs
        pattern = str(Path(cls.base_dir) / "roles" / "sys-*")
        cls.actual_dirs = [d for d in glob.glob(pattern) if Path(d).is_dir()]

    def test_sys_roles_application_id(self):
        for role_dir in self.actual_dirs:
            name = Path(role_dir).name
            prefix = f"sys-{name.removeprefix('sys-')}"
            vars_file = str(Path(role_dir) / "vars" / "main.yml")
            if prefix in self.invokable_prefixes:
                # must exist with id
                self.assertTrue(
                    Path(vars_file).is_file(),
                    f"Missing vars/main.yml for invokable role {prefix}",
                )
                with Path(vars_file).open() as f:
                    content = yaml.safe_load(f) or {}
                self.assertIn(
                    "application_id",
                    content,
                    f"Expected 'application_id' in {vars_file} for invokable role {prefix}",
                )
            else:
                # if exists, must not contain id
                if not Path(vars_file).is_file():
                    continue
                with Path(vars_file).open() as f:
                    content = yaml.safe_load(f) or {}
                self.assertNotIn(
                    "application_id",
                    content,
                    f"Unexpected 'application_id' in {vars_file} for non-invokable role {prefix}",
                )


if __name__ == "__main__":
    unittest.main()
    unittest.main()
