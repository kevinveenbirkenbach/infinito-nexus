# tests/unit/module_utils/test_invokable.py
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

import yaml

import module_utils.invokable as inv


class TestInvokable(TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="invokable_modutils_test_"))
        self.roles_dir = self.tmp / "roles"
        self.roles_dir.mkdir(parents=True, exist_ok=True)
        self.categories_file = self.roles_dir / "categories.yml"

        # This structure triggers the YAML fallback in _get_invokable_paths()
        # because it expects "categories", but we will patch _get_invokable_paths() anyway
        with self.categories_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "categories": [
                        {"invokable_paths": ["web-app", "update", "util-desk"]}
                    ]
                },
                f,
            )

        def mk_role(name: str, application_id: str | None = None) -> None:
            rd = self.roles_dir / name
            (rd / "vars").mkdir(parents=True, exist_ok=True)
            if application_id is not None:
                with (rd / "vars" / "main.yml").open("w", encoding="utf-8") as f:
                    yaml.safe_dump({"application_id": application_id}, f)
            else:
                with (rd / "vars" / "main.yml").open("w", encoding="utf-8") as f:
                    yaml.safe_dump({}, f)

        mk_role("web-app-nextcloud", "web-app-nextcloud")
        mk_role("web-app-matomo", "matomo-app")
        mk_role("web-svc-nginx", None)  # not invokable by our patched paths
        mk_role("update", None)  # exact match
        mk_role("util-desk-custom", None)  # prefix match

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_list_invokable_app_ids(self) -> None:
        with patch.object(inv, "_repo_root", return_value=self.tmp):
            with patch.object(
                inv,
                "_get_invokable_paths",
                return_value=["web-app", "update", "util-desk"],
            ):
                got = inv.list_invokable_app_ids()

        self.assertEqual(
            got,
            sorted(["web-app-nextcloud", "matomo-app", "update", "util-desk-custom"]),
        )

    def test_list_invokables_by_type(self) -> None:
        with patch.object(inv, "_repo_root", return_value=self.tmp):
            with patch.object(
                inv,
                "_get_invokable_paths",
                return_value=["web-app", "update", "util-desk"],
            ):
                grouped = inv.list_invokables_by_type()

        # server: web-app-* minus excluded oauth2 proxy (not present in test)
        self.assertIn("server", grouped)
        self.assertIn("workstation", grouped)
        self.assertIn("universal", grouped)

        self.assertEqual(grouped["server"], sorted(["web-app-nextcloud", "matomo-app"]))
        self.assertEqual(grouped["workstation"], sorted(["util-desk-custom"]))

        # universal = invokable - (server ∪ workstation) -> update remains
        self.assertEqual(grouped["universal"], ["update"])

    def test_list_invokables_by_type_exclude(self) -> None:
        # Ensure exclude regex is honored
        rd = self.roles_dir / "web-app-oauth2-proxy"
        (rd / "vars").mkdir(parents=True, exist_ok=True)
        with (rd / "vars" / "main.yml").open("w", encoding="utf-8") as f:
            yaml.safe_dump({}, f)

        with patch.object(inv, "_repo_root", return_value=self.tmp):
            with patch.object(
                inv,
                "_get_invokable_paths",
                return_value=["web-app", "update", "util-desk"],
            ):
                grouped = inv.list_invokables_by_type()

        self.assertNotIn("web-app-oauth2-proxy", grouped["server"])

    def test_types_from_group_names(self) -> None:
        with patch.object(inv, "_repo_root", return_value=self.tmp):
            with patch.object(
                inv,
                "_get_invokable_paths",
                return_value=["web-app", "update", "util-desk"],
            ):
                got = inv.types_from_group_names(
                    [
                        "all",  # not invokable -> ignored
                        "web-app-nextcloud",  # invokable + matches server rule
                        "util-desk-custom",  # invokable + matches workstation rule
                        "update",  # invokable leftover -> universal
                        "foo",  # not invokable -> ignored
                    ]
                )

        self.assertEqual(got, ["server", "universal", "workstation"])


if __name__ == "__main__":
    main()
