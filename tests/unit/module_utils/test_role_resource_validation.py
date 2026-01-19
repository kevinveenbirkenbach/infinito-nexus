from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stderr
from io import StringIO

from module_utils.role_resource_validation import filter_roles_by_min_storage


class TestRoleResourceValidation(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_filters_by_min_storage_and_emits_warnings(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            # Create minimal categories.yml so get_entity_name("web-app-foo") => "foo"
            self._write(
                root / "roles" / "categories.yml",
                "roles:\n  web:\n    app: {}\n",
            )

            # Role A: should be filtered OUT (50GB > 12GB)
            self._write(
                root / "roles" / "web-app-bigbluebutton" / "config" / "main.yml",
                "docker:\n  services:\n    bigbluebutton:\n      min_storage: 50GB\n",
            )

            # Role B: should be kept (2GB <= 12GB)
            self._write(
                root / "roles" / "web-app-mediawiki" / "config" / "main.yml",
                "docker:\n  services:\n    mediawiki:\n      min_storage: 2GB\n",
            )

            # Role C: missing min_storage -> should be kept (treated as 0GB) + warning
            self._write(
                root / "roles" / "web-app-nextcloud" / "config" / "main.yml",
                "docker:\n  services:\n    nextcloud:\n      image: nextcloud\n",
            )

            roles = ["web-app-bigbluebutton", "web-app-mediawiki", "web-app-nextcloud"]

            buf = StringIO()
            cwd = os.getcwd()
            try:
                os.chdir(
                    root
                )  # important: get_entity_name searches for roles/categories.yml via cwd
                with redirect_stderr(buf):
                    kept = filter_roles_by_min_storage(
                        role_names=roles,
                        required_storage="12GB",
                        emit_warnings=True,
                        roles_root="roles",
                    )
            finally:
                os.chdir(cwd)

            # BBB must be filtered out
            self.assertNotIn("web-app-bigbluebutton", kept)

            # MediaWiki and Nextcloud kept
            self.assertIn("web-app-mediawiki", kept)
            self.assertIn("web-app-nextcloud", kept)

            # Warnings should include:
            stderr = buf.getvalue()
            self.assertIn("requires", stderr)  # for BBB too large
            self.assertIn(
                "Missing key docker.services.nextcloud.min_storage", stderr
            )  # for missing key

    def test_accepts_numeric_required_storage(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            self._write(
                root / "roles" / "categories.yml",
                "roles:\n  web:\n    app: {}\n",
            )
            self._write(
                root / "roles" / "web-app-foo" / "config" / "main.yml",
                "docker:\n  services:\n    foo:\n      min_storage: 2GB\n",
            )

            cwd = os.getcwd()
            try:
                os.chdir(root)
                kept = filter_roles_by_min_storage(
                    role_names=["web-app-foo"],
                    required_storage=12,  # numeric accepted (treated as GB)
                    emit_warnings=False,
                    roles_root="roles",
                )
            finally:
                os.chdir(cwd)

            self.assertEqual(kept, ["web-app-foo"])


if __name__ == "__main__":
    unittest.main()
