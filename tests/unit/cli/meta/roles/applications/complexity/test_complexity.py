from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.meta.roles.applications.complexity.__main__ import (
    compute_complexity_rows,
)
from utils.roles.mapping import ROLE_FILE_META_SERVICES, ROLE_FILE_VARS_MAIN


def _mk_role(
    roles_dir: Path,
    role: str,
    services_yaml: str,
) -> None:
    role_dir = roles_dir / role
    vars_file = role_dir / ROLE_FILE_VARS_MAIN
    services_file = role_dir / ROLE_FILE_META_SERVICES
    vars_file.parent.mkdir(parents=True, exist_ok=True)
    services_file.parent.mkdir(parents=True, exist_ok=True)
    vars_file.write_text(f"application_id: {role}\n", encoding="utf-8")
    services_file.write_text(services_yaml, encoding="utf-8")


class TestComplexityRows(unittest.TestCase):
    def _build_chain_roles(self, roles_dir: Path) -> None:
        # r1: provider only
        _mk_role(
            roles_dir,
            "r1",
            "r1:\n  enabled: true\n  shared: true\n",
        )
        # r2: provider, consumes r1 with literal-true flags
        _mk_role(
            roles_dir,
            "r2",
            (
                "r2:\n  enabled: true\n  shared: true\n"
                "r1:\n  enabled: true\n  shared: true\n"
            ),
        )
        # r3: provider, consumes r2 with literal-true flags
        _mk_role(
            roles_dir,
            "r3",
            (
                "r3:\n  enabled: true\n  shared: true\n"
                "r2:\n  enabled: true\n  shared: true\n"
            ),
        )

    def test_chain_default_sort_by_points(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()
            self._build_chain_roles(roles_dir)

            rows = compute_complexity_rows(roles_dir)
            rows.sort(key=lambda r: (r[1], r[0]))

            self.assertEqual([r[0] for r in rows], ["r1", "r2", "r3"])
            self.assertEqual([r[1] for r in rows], [0, 1, 2])
            self.assertEqual(rows[0][2], [])
            self.assertEqual(rows[1][2], ["r1"])
            # r3 -> r2 -> r1 (BFS reaches r2 first, then r1)
            self.assertEqual(rows[2][2], ["r2", "r1"])

    def test_group_names_flag_toggles_dynamic_truth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            # provider
            _mk_role(
                roles_dir,
                "r1",
                "r1:\n  enabled: true\n  shared: true\n",
            )
            # consumer using the dynamic-flag form
            _mk_role(
                roles_dir,
                "r2",
                (
                    "r2:\n  enabled: true\n  shared: true\n"
                    "r1:\n"
                    "  enabled: \"{{ 'r1' in group_names }}\"\n"
                    "  shared: \"{{ 'r1' in group_names }}\"\n"
                ),
            )

            with_groups = compute_complexity_rows(roles_dir, include_group_names=True)
            without_groups = compute_complexity_rows(
                roles_dir, include_group_names=False
            )

            with_groups_map = {row[0]: row[1] for row in with_groups}
            without_groups_map = {row[0]: row[1] for row in without_groups}

            self.assertEqual(with_groups_map["r2"], 1)
            self.assertEqual(without_groups_map["r2"], 0)
            self.assertEqual(with_groups_map["r1"], 0)
            self.assertEqual(without_groups_map["r1"], 0)

    def test_self_is_not_counted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            # r1 declares itself shared+enabled (provider role).
            # Its own primary entry MUST NOT inflate its dep count.
            _mk_role(
                roles_dir,
                "r1",
                "r1:\n  enabled: true\n  shared: true\n",
            )

            rows = compute_complexity_rows(roles_dir)
            row_map = {row[0]: row for row in rows}
            self.assertEqual(row_map["r1"][1], 0)
            self.assertEqual(row_map["r1"][2], [])

    def test_non_application_roles_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td) / "roles"
            roles_dir.mkdir()

            # role without vars/main.yml -> not an application -> skipped
            non_app_services = roles_dir / "non-app" / ROLE_FILE_META_SERVICES
            non_app_services.parent.mkdir(parents=True)
            non_app_services.write_text(
                "x:\n  enabled: true\n  shared: true\n", encoding="utf-8"
            )

            _mk_role(
                roles_dir,
                "r1",
                "r1:\n  enabled: true\n  shared: true\n",
            )

            rows = compute_complexity_rows(roles_dir)
            names = [row[0] for row in rows]
            self.assertEqual(names, ["r1"])


if __name__ == "__main__":
    unittest.main()
