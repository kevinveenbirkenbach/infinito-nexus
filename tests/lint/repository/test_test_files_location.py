from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


class TestTestFilesLocation(unittest.TestCase):
    """
    Test-linter that enforces every `test_*.py` file to live under the
    top-level `tests/` directory.

    Files ignored by `.gitignore` are skipped (via `git ls-files
    --exclude-standard`), so generated artefacts under e.g. build/ or venvs
    don't trigger failures.
    """

    def test_no_test_files_outside_tests_dir(self):
        root = repo_root()
        result = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        offenders = []
        for line in result.stdout.splitlines():
            path = line.strip()
            if not path:
                continue
            name = path.rsplit("/", 1)[-1]
            if not name.startswith("test_") or not name.endswith(".py"):
                continue
            if path == "tests" or path.startswith("tests/"):
                continue
            offenders.append(path)

        if offenders:
            self.fail(
                "Found `test_*.py` files outside the top-level `tests/` "
                "directory. Move them under `tests/` (or add them to "
                "`.gitignore` if they are not real tests):\n"
                + "\n".join(f"- {p}" for p in sorted(offenders))
            )


if __name__ == "__main__":
    unittest.main()
