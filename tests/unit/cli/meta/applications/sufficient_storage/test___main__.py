from __future__ import annotations

import os
import unittest
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


class TestSufficientStorageCLI(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_cli_filters_and_emits_warnings(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            # Minimal repo layout needed by get_entity_name via cwd
            self._write(
                root / "roles" / "categories.yml",
                "roles:\n  web:\n    app: {}\n",
            )

            self._write(
                root / "roles" / "web-app-bigbluebutton" / "config" / "main.yml",
                "docker:\n  services:\n    bigbluebutton:\n      min_storage: 50GB\n",
            )

            self._write(
                root / "roles" / "web-app-mediawiki" / "config" / "main.yml",
                "docker:\n  services:\n    mediawiki:\n      min_storage: 2GB\n",
            )

            # Run module from *real repo code*, but set cwd to temp root
            # so roles/categories.yml and roles/* exist.
            env = os.environ.copy()
            cmd = [
                sys.executable,
                "-m",
                "cli.meta.applications.sufficient_storage",
                "--roles",
                "web-app-bigbluebutton",
                "web-app-mediawiki",
                "--required-storage",
                "12GB",
                "--warnings",
                "--roles-root",
                str(root / "roles"),
            ]

            # Important: cwd must be temp root so get_entity_name finds roles/categories.yml
            proc = subprocess.run(
                cmd,
                cwd=str(root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            # stdout: kept roles (space-separated)
            self.assertIn("web-app-mediawiki", proc.stdout)
            self.assertNotIn("web-app-bigbluebutton", proc.stdout)

            # stderr: warnings (your code prints ::warning to stderr now)
            self.assertIn("::warning", proc.stderr)
            self.assertIn("requires", proc.stderr)


if __name__ == "__main__":
    unittest.main()
