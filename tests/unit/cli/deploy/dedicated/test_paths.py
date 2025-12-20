from __future__ import annotations

import os
import unittest

from cli.deploy.dedicated import paths


class TestPaths(unittest.TestCase):
    def test_repo_root_resolution_matches_expected_parents(self):
        # paths.py is: <repo>/cli/deploy/dedicated/paths.py
        here = os.path.realpath(paths.__file__)
        dedicated_dir = os.path.dirname(here)
        deploy_dir = os.path.dirname(dedicated_dir)
        cli_dir = os.path.dirname(deploy_dir)
        expected_repo_root = os.path.dirname(cli_dir)

        self.assertEqual(paths.REPO_ROOT, expected_repo_root)

    def test_derived_paths_are_consistent(self):
        self.assertEqual(paths.CLI_ROOT, os.path.join(paths.REPO_ROOT, "cli"))
        self.assertEqual(
            paths.PLAYBOOK_PATH, os.path.join(paths.REPO_ROOT, "playbook.yml")
        )
        self.assertEqual(
            paths.MODES_FILE,
            os.path.join(paths.REPO_ROOT, "group_vars", "all", "01_modes.yml"),
        )
        self.assertEqual(
            paths.INVENTORY_VALIDATOR_PATH,
            os.path.join(
                paths.REPO_ROOT, "cli", "validate", "inventory", "__main__.py"
            ),
        )


if __name__ == "__main__":
    unittest.main()
