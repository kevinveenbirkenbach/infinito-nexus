"""Lint check: no README.md files allowed under docs/.

Documentation files under docs/ MUST be linked to each other directly
and are automatically indexed via the root index.rst toctree glob.
README.md files in docs/ are therefore redundant and MUST NOT exist.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.STDOUT,
        )
        rel_paths = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return [root / rel for rel in rel_paths]
    except Exception:
        return [p for p in root.rglob("*") if p.is_file()]


class TestNoReadmeInDocs(unittest.TestCase):
    def test_no_readme_md_under_docs(self) -> None:
        """docs/ MUST NOT contain README.md files.

        Documentation files are linked to each other directly and are
        automatically indexed via the root index.rst toctree glob.
        Add cross-links between .md files instead of using README.md as
        an index.
        """
        root = repo_root()
        docs_root = root / "docs"

        violations = [
            path.relative_to(root).as_posix()
            for path in tracked_files(root)
            if path.name == "README.md" and path.is_relative_to(docs_root)
        ]

        if violations:
            msg = (
                "README.md files are not allowed under docs/. "
                "Link docs files to each other directly — they are "
                "automatically indexed via the root index.rst toctree glob.\n"
                "Found:\n" + "\n".join(f"  {v}" for v in sorted(violations))
            )
            self.fail(msg)


if __name__ == "__main__":
    unittest.main()
