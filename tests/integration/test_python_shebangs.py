#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


class TestPythonShebangs(unittest.TestCase):
    EXPECTED_PYTHON_SHEBANG = "#!/usr/bin/env python3"

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def _tracked_files(self) -> list[Path]:
        try:
            out = subprocess.check_output(
                ["git", "-C", str(self.repo_root), "ls-files", "-z"],
                stderr=subprocess.STDOUT,
            )
            rel_paths = [
                p for p in out.decode("utf-8", errors="replace").split("\0") if p
            ]
            return [self.repo_root / p for p in rel_paths]
        except Exception:
            files: list[Path] = []
            for root, dirs, names in os.walk(self.repo_root):
                dirs[:] = [d for d in dirs if d != ".git"]
                for name in names:
                    files.append(Path(root) / name)
            return files

    @staticmethod
    def _first_line(path: Path) -> str:
        with path.open("rb") as fh:
            line = fh.readline(4096)
        return line.decode("utf-8", errors="replace").strip()

    def test_python_shebangs_are_portable(self):
        violations: list[str] = []

        for path in self._tracked_files():
            if not path.is_file():
                continue

            first_line = self._first_line(path)
            if not first_line.startswith("#!"):
                continue

            # Only validate shebangs that invoke Python.
            if "python" not in first_line.lower():
                continue

            if first_line != self.EXPECTED_PYTHON_SHEBANG:
                rel = path.relative_to(self.repo_root).as_posix()
                violations.append(f"{rel}: {first_line}")

        if violations:
            self.fail(
                "Found non-portable Python shebangs.\n"
                "Required shebang: '#!/usr/bin/env python3'\n\n"
                "Why this is necessary:\n"
                "- Hardcoded interpreter paths like '/usr/bin/python' are not guaranteed "
                "to exist across distros/images.\n"
                "- Using '/usr/bin/env python3' resolves python3 via PATH and keeps scripts "
                "portable in CI, containers, and systemd services.\n"
                "- Wrong shebangs can lead to runtime failures such as "
                "'No such file or directory' / status=203/EXEC.\n\n"
                "Offending files:\n- " + "\n- ".join(violations)
            )


if __name__ == "__main__":
    unittest.main()
