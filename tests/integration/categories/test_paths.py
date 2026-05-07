import os
import unittest
from pathlib import Path

import yaml


class TestCategoryPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load categories.yml
        file_path = str(
            Path(
                str(
                    Path(str(Path(__file__).parent))
                    / ".."
                    / ".."
                    / ".."
                    / "roles"
                    / "categories.yml"
                )
            ).resolve()
        )
        with Path(file_path).open() as f:
            data = yaml.safe_load(f)
        cls.roles_def = data["roles"]

        # List of actual directories under roles/
        roles_dir = str(
            Path(
                str(Path(str(Path(__file__).parent)) / ".." / ".." / ".." / "roles")
            ).resolve()
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
        missing.extend(
            name
            for name in expected
            if not any(name in dirname for dirname in self.existing_dirs)
        )

        if missing:
            self.fail(f"Missing role directories for: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    unittest.main()
