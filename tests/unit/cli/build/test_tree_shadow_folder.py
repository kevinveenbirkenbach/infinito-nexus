import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch

# Absolute path to the tree/__main__.py script
SCRIPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../cli/build/tree/__main__.py")
)

class TestTreeShadowFolder(unittest.TestCase):
    def setUp(self):
        # Create a temporary roles directory and a dummy role
        self.roles_dir = tempfile.mkdtemp()
        self.role_name = "dummyrole"
        self.role_path = os.path.join(self.roles_dir, self.role_name)
        os.makedirs(os.path.join(self.role_path, "meta"))

        # Create a temporary shadow folder
        self.shadow_dir = tempfile.mkdtemp()

        # Patch sys.argv so the script picks up our dirs
        self.orig_argv = sys.argv[:]
        sys.argv = [
            SCRIPT_PATH,
            "-d", self.roles_dir,
            "-s", self.shadow_dir,
            "-o", "json"
        ]

        # Ensure project root is on sys.path so `import cli.build.tree` works
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../")
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

    def tearDown(self):
        # Restore original argv and clean up
        sys.argv = self.orig_argv
        shutil.rmtree(self.roles_dir)
        shutil.rmtree(self.shadow_dir)

    @patch("cli.build.tree.build_mappings")
    @patch("cli.build.tree.output_graph")
    def test_tree_json_written_to_shadow_folder(self, mock_output_graph, mock_build_mappings):
        # Prepare the dummy graph that build_mappings should return
        dummy_graph = {"dummy": {"test": 42}}
        mock_build_mappings.return_value = dummy_graph

        # Import the script module by name (so our @patch applies) and call main()
        import importlib
        tree_mod = importlib.import_module("cli.build.tree")
        tree_mod.main()

        # Verify that tree.json was written into the shadow folder
        expected_tree_path = os.path.join(
            self.shadow_dir, self.role_name, "meta", "tree.json"
        )
        self.assertTrue(
            os.path.isfile(expected_tree_path),
            f"tree.json not found at {expected_tree_path}"
        )

        # Verify contents match our dummy_graph
        with open(expected_tree_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data, dummy_graph, "tree.json content mismatch")

        # Ensure that no tree.json was written to the real meta/ folder
        original_tree_path = os.path.join(self.role_path, "meta", "tree.json")
        self.assertFalse(
            os.path.exists(original_tree_path),
            "tree.json should NOT be written to the real meta/ folder"
        )

if __name__ == "__main__":
    unittest.main()
