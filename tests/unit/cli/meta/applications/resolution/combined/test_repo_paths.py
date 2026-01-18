from __future__ import annotations

import unittest
from pathlib import Path

from cli.meta.applications.resolution.combined import repo_paths


class TestRepoPaths(unittest.TestCase):
    def test_roles_dir_is_path(self) -> None:
        # This is a very light test: just ensure it returns a Path
        rdir = repo_paths.roles_dir()
        self.assertIsInstance(rdir, Path)

    def test_role_meta_and_vars_paths_are_paths(self) -> None:
        meta = repo_paths.role_meta_path("web-app-x")
        vars_ = repo_paths.role_vars_path("web-app-x")
        self.assertIsInstance(meta, Path)
        self.assertIsInstance(vars_, Path)
        self.assertTrue(str(meta).endswith("roles/web-app-x/meta/main.yml"))
        self.assertTrue(str(vars_).endswith("roles/web-app-x/vars/main.yml"))
