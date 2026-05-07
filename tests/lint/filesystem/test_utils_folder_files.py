"""Lint check: tracked files under utils/ must be Python helpers.

README.md files are ignored because they are documentation-only exceptions.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


def tracked_files(root: Path) -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.STDOUT,
        )
        rel_paths = [path for path in output.decode("utf-8").split("\0") if path]
        return [root / rel_path for rel_path in rel_paths]
    except Exception:
        return [
            path
            for path in root.rglob("*")  # noqa: project-walk
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
        ]


class TestUtilsFolderFiles(unittest.TestCase):
    def test_utils_contains_only_py_files(self) -> None:
        root = repo_root()
        utils_root = root / "utils"

        violations = [
            path.relative_to(root).as_posix()
            for path in tracked_files(root)
            if path.is_relative_to(utils_root)
            and path.name != "README.md"
            and path.suffix != ".py"
        ]

        self.assertEqual(
            violations,
            [],
            "Tracked files under utils/ must end with .py "
            "(README.md is allowed).\nFound:\n"
            + "\n".join(f"  {path}" for path in sorted(violations)),
        )


if __name__ == "__main__":
    unittest.main()
