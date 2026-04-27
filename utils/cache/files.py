"""Process-level cached filesystem helpers for project-tree scans.

Many integration/lint tests and CLI tools walk the whole repo and read every
matching file. Doing that N times per process is wasteful — the tree doesn't
change during a run. These helpers walk the tree once per process and memoise
both the path list and file contents, so every caller after the first one pays
near-zero cost.

Usage:

    from utils.cache.files import iter_project_files, read_text

    for path in iter_project_files(extensions=(".yml", ".yml.j2"), exclude_tests=True):
        content = read_text(path)
        ...

`PROJECT_ROOT` is the repo root derived from this file's location.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable, Iterator, Tuple

from .base import PROJECT_ROOT

# Directories never worth descending into during project-tree scans.
_DEFAULT_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
    }
)


@lru_cache(maxsize=1)
def _all_project_files() -> tuple[str, ...]:
    """One-shot filesystem walk from PROJECT_ROOT.

    Returns absolute paths as a tuple (immutable → safe to cache).
    Pruned at walk-time by `_DEFAULT_SKIP_DIRS`, since those dirs are never
    relevant for any project-tree test and descending into them is pure waste.
    """
    root_str = str(PROJECT_ROOT)
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True):
        # prune in-place (topdown=True): stops descent into skipped dirs
        dirnames[:] = [d for d in dirnames if d not in _DEFAULT_SKIP_DIRS]
        for fn in filenames:
            paths.append(os.path.join(dirpath, fn))
    return tuple(paths)


def iter_project_files(
    *,
    extensions: Iterable[str] | None = None,
    exclude_tests: bool = False,
    exclude_dirs: Iterable[str] | None = None,
) -> Iterator[str]:
    """Yield absolute paths of project files matching the filter.

    Args:
        extensions: Suffix strings (e.g. ``(".yml", ".yaml.j2")``). Matching is
            case-insensitive via plain string suffix. ``None`` yields all files.
        exclude_tests: Skip everything under ``<root>/tests/``.
        exclude_dirs: Additional top-level-or-nested directory names to skip.
            Matched by path-component containment, not by prefix. E.g.
            ``exclude_dirs=("docs",)`` skips any file whose path contains a
            ``docs`` segment.
    """
    all_files = _all_project_files()
    tests_prefix = os.path.join(str(PROJECT_ROOT), "tests") + os.sep
    ext_lower = tuple(e.lower() for e in extensions) if extensions else None
    exclude_dirs_set = set(exclude_dirs) if exclude_dirs else None

    for path in all_files:
        if exclude_tests and path.startswith(tests_prefix):
            continue
        if exclude_dirs_set is not None:
            # Cheap path-segment check; avoids splitting the full path.
            rel = os.path.relpath(path, str(PROJECT_ROOT))
            segments = rel.split(os.sep)
            if exclude_dirs_set.intersection(segments):
                continue
        if ext_lower is not None:
            lower = path.lower()
            if not any(lower.endswith(e) for e in ext_lower):
                continue
        yield path


@lru_cache(maxsize=8192)
def read_text(path: str) -> str:
    """Return the UTF-8 text content of a file; cached process-wide.

    Raises OSError / UnicodeDecodeError unchanged — callers that scan arbitrary
    files can wrap this in try/except if non-UTF-8 blobs may appear.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def iter_project_files_with_content(
    *,
    extensions: Iterable[str] | None = None,
    exclude_tests: bool = False,
    exclude_dirs: Iterable[str] | None = None,
) -> Iterator[Tuple[str, str]]:
    """Yield ``(path, content)`` for matching files; content is cached.

    Files that fail to read (permission errors, non-UTF-8) are silently
    skipped — that matches the prior caller behaviour of wrapping
    ``open().read()`` in a bare ``try/except Exception: continue``.
    """
    for path in iter_project_files(
        extensions=extensions,
        exclude_tests=exclude_tests,
        exclude_dirs=exclude_dirs,
    ):
        try:
            content = read_text(path)
        except (OSError, UnicodeDecodeError):
            continue
        yield path, content


def _reset() -> None:
    """Test-only helper: clear the project-walk and file-content caches.

    Named ``_reset`` for parity with the per-domain reset helpers in
    sibling modules; ``utils.cache._reset_cache_for_tests`` orchestrates
    calls to all of them.
    """
    _all_project_files.cache_clear()
    read_text.cache_clear()
