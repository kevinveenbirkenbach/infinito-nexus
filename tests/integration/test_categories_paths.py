import os
import unittest
import yaml


class TestCategoryPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load categories.yml
        file_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "roles", "categories.yml"
            )
        )
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        cls.roles_def = data["roles"]

        # List of actual directories under roles/
        roles_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "roles")
        )
        cls.existing_dirs = os.listdir(roles_dir)

    def test_all_category_paths_exist(self):
        expected = set()

        for top_key, attrs in self.roles_def.items():
            # Top-level category
            expected.add(top_key)

            # Nested subcategories (keys other than metadata)
            for sub_key in attrs:
                # Skip metadata keys
                if sub_key in ("title", "description", "icon", "children", "invokable"):
                    continue
                expected.add(f"{top_key}-{sub_key}")

        missing = []
        for name in expected:
            if not any(name in dirname for dirname in self.existing_dirs):
                missing.append(name)

        if missing:
            self.fail(f"Missing role directories for: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    unittest.main()
