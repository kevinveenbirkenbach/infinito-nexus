# test/unit/cli/meta/roles/test_lifecycle_filter.py
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cli.meta.roles.lifecycle_filter.__main__ import _extract_lifecycle, filter_roles


def _write_meta(role_dir: Path, lifecycle_value: str | None) -> None:
    meta_dir = role_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    if lifecycle_value is None:
        content = "galaxy_info:\n  role_name: dummy\n"
    else:
        content = f"galaxy_info:\n  lifecycle: {lifecycle_value}\n"

    (meta_dir / "main.yml").write_text(content, encoding="utf-8")


def _write_meta_stage(role_dir: Path, stage_value: str) -> None:
    meta_dir = role_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    content = "galaxy_info:\n  lifecycle:\n    stage: " + stage_value + "\n"
    (meta_dir / "main.yml").write_text(content, encoding="utf-8")


class TestLifecycleFilter(unittest.TestCase):
    def test_extract_lifecycle_string_lowercases_and_strips(self) -> None:
        meta = {"galaxy_info": {"lifecycle": "  StAbLe  "}}
        self.assertEqual(_extract_lifecycle(meta), "stable")

    def test_extract_lifecycle_dict_stage_supported(self) -> None:
        meta = {"galaxy_info": {"lifecycle": {"stage": "RC"}}}
        self.assertEqual(_extract_lifecycle(meta), "rc")

    def test_filter_roles_whitelist_matches_only_requested_statuses(self) -> None:
        with TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            _write_meta(roles_dir / "role-a", "stable")
            _write_meta(roles_dir / "role-b", "beta")
            _write_meta(roles_dir / "role-c", "deprecated")
            _write_meta(roles_dir / "role-missing", None)

            result = filter_roles(
                roles_dir=roles_dir,
                mode="whitelist",
                statuses={"stable", "rc"},
                selection=None,
            )

            self.assertEqual(result, ["role-a"])

    def test_filter_roles_blacklist_includes_missing_by_default(self) -> None:
        with TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            _write_meta(roles_dir / "role-a", "stable")
            _write_meta(roles_dir / "role-b", "deprecated")
            _write_meta(roles_dir / "role-c", "eol")
            _write_meta(roles_dir / "role-missing", None)

            result = filter_roles(
                roles_dir=roles_dir,
                mode="blacklist",
                statuses={"deprecated", "eol"},
                selection=None,
                include_missing_lifecycle_on_blacklist=True,
            )

            self.assertEqual(result, ["role-a", "role-missing"])

    def test_filter_roles_blacklist_can_exclude_missing(self) -> None:
        with TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            _write_meta(roles_dir / "role-a", "stable")
            _write_meta(roles_dir / "role-b", "deprecated")
            _write_meta(roles_dir / "role-missing", None)

            result = filter_roles(
                roles_dir=roles_dir,
                mode="blacklist",
                statuses={"deprecated"},
                selection=None,
                include_missing_lifecycle_on_blacklist=False,
            )

            self.assertEqual(result, ["role-a"])

    def test_filter_roles_selection_limits_output(self) -> None:
        with TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            _write_meta(roles_dir / "role-a", "stable")
            _write_meta(roles_dir / "role-b", "stable")
            _write_meta(roles_dir / "role-c", "beta")

            result = filter_roles(
                roles_dir=roles_dir,
                mode="whitelist",
                statuses={"stable"},
                selection={"role-b", "role-c"},
            )

            self.assertEqual(result, ["role-b"])

    def test_filter_roles_supports_lifecycle_stage_dict(self) -> None:
        with TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            _write_meta_stage(roles_dir / "role-rc", "RC")
            _write_meta(roles_dir / "role-stable", "stable")

            result = filter_roles(
                roles_dir=roles_dir,
                mode="whitelist",
                statuses={"rc"},
                selection=None,
            )

            self.assertEqual(result, ["role-rc"])


if __name__ == "__main__":
    unittest.main()
