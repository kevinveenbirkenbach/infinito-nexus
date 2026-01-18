# tests/unit/cli/meta/applications/resolution/combined/test_resolver.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli.meta.applications.resolution.combined.errors import CombinedResolutionError
from cli.meta.applications.resolution.combined import repo_paths
from cli.meta.applications.resolution.combined.resolver import CombinedResolver


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


class TestCombinedResolver(unittest.TestCase):
    def test_resolve_orders_prereqs_first_run_after_then_deps(self) -> None:
        """
        Graph:
          app
            run_after: ra1
            dependencies: dep1 (app), sys1 (non-app, ignored)

          ra1 run_after: ra2
          dep1 dependencies: dep2 (app)

        Expected topological order:
          ra2 ra1 dep2 dep1   (start role excluded)
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            _mk_role(root, "app", app_id="app")
            _mk_role(root, "ra1", app_id="ra1")
            _mk_role(root, "ra2", app_id="ra2")
            _mk_role(root, "dep1", app_id="dep1")
            _mk_role(root, "dep2", app_id="dep2")
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
            _write_meta(
                root,
                "ra1",
                """
galaxy_info:
  run_after: [ra2]
""",
            )
            _write_meta(
                root,
                "dep1",
                """
dependencies:
  - dep2
""",
            )

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                resolver = CombinedResolver()
                out = resolver.resolve("app")
                self.assertEqual(out, ["ra2", "ra1", "dep2", "dep1"])

    def test_cycle_detection_across_combined_graph(self) -> None:
        """
        app run_after: a
        a dependencies: app
        => cycle app -> a -> app
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            _mk_role(root, "app", app_id="app")
            _mk_role(root, "a", app_id="a")

            _write_meta(
                root,
                "app",
                """
galaxy_info:
  run_after: [a]
""",
            )
            _write_meta(
                root,
                "a",
                """
dependencies:
  - app
""",
            )

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                resolver = CombinedResolver()
                with self.assertRaises(CombinedResolutionError):
                    resolver.resolve("app")
