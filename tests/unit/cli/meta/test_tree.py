import unittest
import tempfile
import shutil
import os
from cli.build import tree


class TestTreeMain(unittest.TestCase):
    def setUp(self):
        # Create a temporary roles directory with a fake role
        self.temp_dir = tempfile.mkdtemp()
        self.role_name = "testrole"
        self.role_path = os.path.join(self.temp_dir, self.role_name)
        os.makedirs(os.path.join(self.role_path, "meta"))

        meta_path = os.path.join(self.role_path, "meta", "main.yml")
        with open(meta_path, "w") as f:
            f.write("galaxy_info:\n  author: test\n  run_after: []\ndependencies: []\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_roles(self):
        roles = list(tree.find_roles(self.temp_dir))
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0][0], self.role_name)

    def test_main_execution_does_not_raise(self):
        # Mocking sys.argv and running main should not raise
        import sys

        old_argv = sys.argv
        sys.argv = ["tree/__main__.py", "-d", self.temp_dir, "-p"]
        try:
            tree.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
