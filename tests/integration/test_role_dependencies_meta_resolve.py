import unittest
import os
import glob
import yaml


class TestRoleDependencies(unittest.TestCase):
    def test_dependencies_exist(self):
        # Determine the path to the roles directory relative to this test file
        tests_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
        roles_dir = os.path.join(project_root, "roles")

        # Find all meta/main.yml files under roles/*/meta/main.yml
        pattern = os.path.join(roles_dir, "*", "meta", "main.yml")
        meta_files = glob.glob(pattern)
        self.assertTrue(
            meta_files, f"No meta/main.yml files found with pattern {pattern}"
        )

        for meta_file in meta_files:
            role_dir = os.path.dirname(os.path.dirname(meta_file))
            role_name = os.path.basename(role_dir)
            with self.subTest(role=role_name):
                # Load the YAML metadata
                with open(meta_file, "r") as f:
                    meta = yaml.safe_load(f) or {}

                # Extract dependencies list
                dependencies = meta.get("dependencies", [])
                self.assertIsInstance(
                    dependencies,
                    list,
                    f"'dependencies' for role '{role_name}' is not a list",
                )

                for dep in dependencies:
                    # Dependencies can be strings or dicts with a 'role' key
                    if isinstance(dep, str):
                        dep_name = dep
                    elif isinstance(dep, dict) and "role" in dep:
                        dep_name = dep["role"]
                    else:
                        self.fail(
                            f"Invalid dependency format {dep!r} in role '{role_name}'"
                        )

                    dep_path = os.path.join(roles_dir, dep_name)
                    # Assert that the dependency role directory exists
                    self.assertTrue(
                        os.path.isdir(dep_path),
                        f"Role '{role_name}' declares dependency '{dep_name}' but '{dep_path}' does not exist",
                    )


if __name__ == "__main__":
    unittest.main()
