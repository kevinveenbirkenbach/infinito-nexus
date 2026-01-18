# tests/unit/cli/meta/applications/resolution/combined/test_tree.py
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli.meta.applications.resolution.combined import repo_paths
from cli.meta.applications.resolution.combined.tree import print_tree


def _mk_role(root: Path, role: str, *, app_id: str | None = None) -> None:
    role_dir = root / "roles" / role
    (role_dir / "meta").mkdir(parents=True, exist_ok=True)
    (role_dir / "vars").mkdir(parents=True, exist_ok=True)
    if app_id is not None:
        (role_dir / "vars" / "main.yml").write_text(
            f"application_id: {app_id}\n", encoding="utf-8"
        )


def _write_meta(root: Path, role: str, text: str) -> None:
    p = root / "roles" / role / "meta" / "main.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestTree(unittest.TestCase):
    def test_tree_prints_groups_and_children(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_role(root, "app", app_id="app")
            _mk_role(root, "ra1", app_id="ra1")
            _mk_role(root, "dep1", app_id="dep1")
            _mk_role(root, "sys1", app_id=None)

            _write_meta(
                root,
                "app",
                """
galaxy_info:
  run_after: [ra1]
dependencies:
  - dep1
  - sys1
""",
            )

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    print_tree("app")
                s = buf.getvalue()
                self.assertIn("app", s)
                self.assertIn("[run_after]", s)
                self.assertIn("[dependencies]", s)
                self.assertIn("ra1", s)
                self.assertIn("dep1", s)
                # sys1 should not appear under dependencies (non-app)
                self.assertNotIn("sys1", s)
