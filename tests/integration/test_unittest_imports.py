# File: tests/integration/test_unittest_imports.py

import os
import unittest


class TestUnittestImports(unittest.TestCase):
    TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_all_test_files_import_unittest(self):
        missing = []

        for root, dirs, files in os.walk(self.TEST_ROOT):
            for filename in files:
                if not filename.endswith(".py"):
                    continue
                # only consider test files named like "test_*.py"
                if not filename.startswith("test_"):
                    continue

                filepath = os.path.join(root, filename)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()

                # check for either import form
                if (
                    "import unittest" not in content
                    and "from unittest import" not in content
                ):
                    rel_path = os.path.relpath(filepath, os.getcwd())
                    missing.append(rel_path)

        if missing:
            self.fail(
                "The following test files do not import unittest:\n"
                + "\n".join(f"- {path}" for path in missing)
            )


if __name__ == "__main__":
    unittest.main()
