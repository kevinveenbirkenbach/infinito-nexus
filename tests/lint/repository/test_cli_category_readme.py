"""Lint guard: every CLI category folder under ``cli/`` MUST carry a
``README.md`` shaped according to
``docs/contributing/artefact/files/cli/readme_md.md``.

A category folder is a directory under ``cli/`` that does NOT contain
its own ``__main__.py`` but has at least one runnable command
underneath. Its ``README.md`` is read by the CLI help system
(:mod:`cli.core.help`) and surfaced as the category title and
description in ``infinito --help``, ``infinito <category>``, and
``infinito --tree``. Empty support packages (no commands anywhere
underneath) are exempt because the help system already filters them
out.

A conformant ``README.md`` has:

1. An H1 heading (line starts with ``# ``) as the very first
   non-blank line.
2. A trailing emoji on that H1 (last non-whitespace character is
   non-ASCII), per the heading-emoji rule in
   ``docs/contributing/documentation.md``.
3. A non-empty, non-heading description paragraph immediately below
   the H1 (separated by exactly one blank line). The first paragraph
   is what the help system extracts.
"""

from __future__ import annotations

import unittest
from typing import TYPE_CHECKING

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

CLI_DIR = PROJECT_ROOT / "cli"
README_NAME = "README.md"
CONVENTION_DOC = "docs/contributing/artefact/files/cli/readme_md.md"


def _has_command_descendant(folder: Path) -> bool:
    if (folder / "__main__.py").is_file():
        return True
    for path in folder.rglob("__main__.py"):
        if "__pycache__" in path.parts:
            continue
        return True
    return False


def _is_category_folder(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    if folder.name == "__pycache__":
        return False
    if "__pycache__" in folder.parts:
        return False
    if (folder / "__main__.py").is_file():
        return False
    return _has_command_descendant(folder)


def _iter_category_folders(cli_dir: Path) -> list[Path]:
    """Return every category folder under ``cli/``, sorted by relative
    path. The ``cli`` package itself is skipped because the global
    help splash already covers the repo-level entry."""
    found = [path for path in cli_dir.rglob("*") if _is_category_folder(path)]
    found.sort(key=lambda p: p.relative_to(cli_dir).as_posix())
    return found


def _has_trailing_emoji(line: str) -> bool:
    """Return True when the last non-whitespace character of ``line``
    is outside the ASCII range. Catches both single-codepoint emoji
    glyphs and the trailing variation selector that pairs with many
    file/tool emojis."""
    stripped = line.rstrip()
    if not stripped:
        return False
    return ord(stripped[-1]) > 0x7F


def _check_readme_shape(readme_path: Path) -> str | None:
    """Validate one README.md against the convention. Returns ``None``
    when the file conforms, otherwise a short violation message."""
    if not readme_path.is_file():
        return f"missing {README_NAME}"

    try:
        text = readme_path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"could not read {README_NAME}: {exc}"

    lines = text.splitlines()
    h1_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            h1_index = index
            break
        return (
            f"first non-blank line is not an H1 heading "
            f"(must start with '# '); got: {stripped!r}"
        )

    if h1_index is None:
        return f"{README_NAME} contains no H1 heading"

    h1_line = lines[h1_index].strip()
    if not _has_trailing_emoji(h1_line):
        return (
            f"H1 {h1_line!r} has no trailing emoji "
            f"(per the heading-emoji rule in documentation.md)"
        )

    # Description paragraph: there must be a blank line after the H1,
    # then a non-blank, non-heading paragraph.
    saw_blank_separator = False
    for line in lines[h1_index + 1 :]:
        stripped = line.strip()
        if not saw_blank_separator:
            if stripped:
                return (
                    "H1 must be followed by a blank line, then the "
                    f"description paragraph; got non-blank: {stripped!r}"
                )
            saw_blank_separator = True
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            return (
                "no description paragraph between the H1 and the "
                "next heading; the help system needs the first "
                "paragraph as the category description"
            )
        return None

    return "no description paragraph found below the H1"


class TestCliCategoryReadme(unittest.TestCase):
    def test_every_category_folder_has_a_conformant_readme(self) -> None:
        self.assertTrue(CLI_DIR.is_dir(), f"cli/ directory not found at: {CLI_DIR}")

        offenders: list[str] = []
        for folder in _iter_category_folders(CLI_DIR):
            issue = _check_readme_shape(folder / README_NAME)
            if issue is not None:
                rel = folder.relative_to(PROJECT_ROOT).as_posix()
                offenders.append(f"{rel}: {issue}")

        if offenders:
            self.fail(
                f"CLI category folder(s) violate the README convention "
                f"described in {CONVENTION_DOC}:\n"
                + "\n".join(f"  - {o}" for o in offenders)
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
