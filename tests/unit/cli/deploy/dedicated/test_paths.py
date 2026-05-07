from __future__ import annotations

import os
import unittest
from pathlib import Path

from cli.deploy.dedicated import paths


class TestPaths(unittest.TestCase):
    def test_repo_root_resolution_matches_expected_parents(self):
        # paths.py is: <repo>/cli/deploy/dedicated/paths.py
        here = os.path.realpath(paths.__file__)
        dedicated_dir = str(Path(here).parent)
        deploy_dir = str(Path(dedicated_dir).parent)
        cli_dir = str(Path(deploy_dir).parent)
        expected_repo_root = str(Path(cli_dir).parent)

        self.assertEqual(paths.PROJECT_ROOT, expected_repo_root)

    def test_derived_paths_are_consistent(self):
        self.assertEqual(paths.CLI_ROOT, str(Path(paths.PROJECT_ROOT) / "cli"))
        self.assertEqual(
            paths.PLAYBOOK_PATH, str(Path(paths.PROJECT_ROOT) / "playbook.yml")
        )
        self.assertEqual(
            paths.MODES_FILE,
            str(Path(paths.PROJECT_ROOT) / "group_vars" / "all" / "01_modes.yml"),
        )
        self.assertEqual(
            paths.INVENTORY_VALIDATOR_PATH,
            str(
                Path(paths.PROJECT_ROOT)
                / "cli"
                / "validate"
                / "inventory"
                / "__main__.py"
            ),
        )


if __name__ == "__main__":
    unittest.main()
