# tests/unit/cli/meta/applications/resolution/affected/test_main.py
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from cli.meta.applications.resolution.affected import __main__ as affected_main
from cli.meta.applications.resolution.combined import repo_paths


def _mk_app_role(root: Path, role: str, app_id: str) -> None:
    role_dir = root / "roles" / role
    (role_dir / "meta").mkdir(parents=True, exist_ok=True)
    (role_dir / "vars").mkdir(parents=True, exist_ok=True)
    (role_dir / "vars" / "main.yml").write_text(
        f"application_id: {app_id}\n", encoding="utf-8"
    )


def _mk_non_app_role(root: Path, role: str) -> None:
    """Create a role folder without ``application_id``."""
    (root / "roles" / role / "meta").mkdir(parents=True, exist_ok=True)


def _write_run_after(root: Path, role: str, run_after: list[str]) -> None:
    p = root / "roles" / role / "meta" / "services.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump({role: {"run_after": run_after}}),
        encoding="utf-8",
    )


def _write_dependencies(root: Path, role: str, deps: list[str]) -> None:
    p = root / "roles" / role / "meta" / "main.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump({"dependencies": deps}),
        encoding="utf-8",
    )


class TestAffected(unittest.TestCase):
    def test_seed_only_when_no_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "leaf", "leaf")
            _mk_app_role(root, "other", "other")

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                self.assertEqual(
                    affected_main.affected_roles(["leaf"]),
                    ["leaf"],
                )

    def test_run_after_consumer_is_included(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "leaf", "leaf")
            _mk_app_role(root, "consumer", "consumer")
            _write_run_after(root, "consumer", ["leaf"])

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                self.assertEqual(
                    affected_main.affected_roles(["leaf"]),
                    ["consumer", "leaf"],
                )

    def test_dependencies_consumer_is_included_transitively(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "leaf", "leaf")
            _mk_app_role(root, "mid", "mid")
            _mk_app_role(root, "top", "top")
            _write_dependencies(root, "mid", ["leaf"])
            _write_dependencies(root, "top", ["mid"])

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                self.assertEqual(
                    affected_main.affected_roles(["leaf"]),
                    ["leaf", "mid", "top"],
                )

    def test_shared_service_consumer_is_included(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "web-app-keycloak", "keycloak")
            _mk_app_role(root, "web-app-consumer", "consumer")
            (root / "roles" / "web-app-consumer" / "meta" / "services.yml").write_text(
                yaml.safe_dump(
                    {
                        "consumer": {},
                        "oidc": {"enabled": True, "shared": True, "flavor": ""},
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                got = affected_main.affected_roles(["web-app-keycloak"])
                self.assertIn("web-app-keycloak", got)
                self.assertIn("web-app-consumer", got)

    def test_unknown_role_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "leaf", "leaf")
            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                with self.assertRaises(SystemExit):
                    affected_main.affected_roles(["does-not-exist"])

    def test_non_modellable_seed_exits_with_sentinel_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_non_app_role(root, "sys-helper")
            _mk_app_role(root, "consumer", "consumer")

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                with self.assertRaises(SystemExit) as ctx:
                    affected_main.affected_roles(["sys-helper"])
                self.assertEqual(
                    ctx.exception.code,
                    affected_main.EXIT_NON_MODELLABLE_SEED,
                )

    def test_non_app_seed_reachable_via_run_after_is_modellable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_non_app_role(root, "sys-helper")
            _mk_app_role(root, "consumer", "consumer")
            _write_run_after(root, "consumer", ["sys-helper"])

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                got = affected_main.affected_roles(["sys-helper"])
            self.assertIn("sys-helper", got)
            self.assertIn("consumer", got)

    def test_main_prints_space_separated_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk_app_role(root, "leaf", "leaf")
            _mk_app_role(root, "consumer", "consumer")
            _write_run_after(root, "consumer", ["leaf"])

            with patch.object(repo_paths, "repo_root_from_here", return_value=root):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    with patch(
                        "sys.argv",
                        ["prog", "--changed-roles", "leaf"],
                    ):
                        affected_main.main()
                self.assertEqual(buf.getvalue().strip(), "consumer leaf")


if __name__ == "__main__":
    unittest.main()
