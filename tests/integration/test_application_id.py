import unittest
import yaml
import os
import glob

from filter_plugins.invokable_paths import get_invokable_paths


class TestSysRolesApplicationId(unittest.TestCase):
    """
    Integration tests for sys-* roles based on categories.yml prefixes:
    For each actual sys-* directory under roles/:
      - If dash-joined prefix is in invokable_paths -> vars/main.yml must exist and contain application_id.
      - Otherwise (non-invokable or undeclared) -> if vars/main.yml exists, it must NOT contain application_id.
    """

    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        cat_file = os.path.join(cls.base_dir, "roles", "categories.yml")
        cls.invokable_prefixes = set(get_invokable_paths(cat_file))
        # collect actual sys dirs
        pattern = os.path.join(cls.base_dir, "roles", "sys-*")
        cls.actual_dirs = [d for d in glob.glob(pattern) if os.path.isdir(d)]

    def test_sys_roles_application_id(self):
        for role_dir in self.actual_dirs:
            name = os.path.basename(role_dir)
            prefix = f"sys-{name[len('sys-') :] if name.startswith('sys-') else name}"
            vars_file = os.path.join(role_dir, "vars", "main.yml")
            if prefix in self.invokable_prefixes:
                # must exist with id
                self.assertTrue(
                    os.path.isfile(vars_file),
                    f"Missing vars/main.yml for invokable role {prefix}",
                )
                with open(vars_file) as f:
                    content = yaml.safe_load(f) or {}
                self.assertIn(
                    "application_id",
                    content,
                    f"Expected 'application_id' in {vars_file} for invokable role {prefix}",
                )
            else:
                # if exists, must not contain id
                if not os.path.isfile(vars_file):
                    continue
                with open(vars_file) as f:
                    content = yaml.safe_load(f) or {}
                self.assertNotIn(
                    "application_id",
                    content,
                    f"Unexpected 'application_id' in {vars_file} for non-invokable role {prefix}",
                )


if __name__ == "__main__":
    unittest.main()
    unittest.main()
