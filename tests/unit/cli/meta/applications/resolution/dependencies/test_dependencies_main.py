# tests/unit/cli/meta/applications/resolution/dependencies/test_dependencies_main.py
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

# Import the module under test
from cli.meta.applications.resolution.dependencies import __main__ as deps_main


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


class TestDependenciesResolution(unittest.TestCase):
    def test_resolve_dependencies_transitively_filters_non_app(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            _mk_role(root, "app", app_id="app")
            _mk_role(root, "app_dep", app_id="app_dep")
            _mk_role(root, "sys_helper", app_id=None)

            _write_meta(
                root,
                "app",
                """
dependencies:
  - app_dep
  - sys_helper
""",
            )

            with patch.object(deps_main, "repo_root_from_here", return_value=root):
                out = deps_main.resolve_dependencies_transitively("app")
                self.assertEqual(out, ["app_dep"])

    def test_main_prints_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            _mk_role(root, "app", app_id="app")
            _mk_role(root, "app_dep", app_id="app_dep")
            _write_meta(
                root,
                "app",
                """
dependencies:
  - app_dep
""",
            )

            with patch.object(deps_main, "repo_root_from_here", return_value=root):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    with patch("sys.argv", ["prog", "app"]):
                        deps_main.main()
                self.assertEqual(buf.getvalue().strip(), "app_dep")
