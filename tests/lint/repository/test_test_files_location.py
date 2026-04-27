from __future__ import annotations

import fnmatch
import os
import unittest
from pathlib import Path

from utils.cache.files import iter_project_files


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


def _load_gitignore_patterns(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for raw in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            # Negation patterns (re-include) are not used in this repo's .gitignore.
            # If someone adds one later, extending this helper is cheap; for now
            # we ignore them so they don't accidentally widen the ignore set.
            continue
        patterns.append(line)
    return patterns


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    """Minimal gitignore matcher covering the shapes used in this repo.

    Supports:
    - Blank lines and `#` comments (filtered in `_load_gitignore_patterns`).
    - Bare-basename patterns (no slash): match any path component by `fnmatch`.
    - Path-qualified patterns (with slash): match from repo root via `fnmatch`,
      including `prefix/*` shorthand for everything under `prefix/`, and plain
      directory prefixes (`foo/bar` ignores anything under `foo/bar/`).
    - Trailing `/` denotes directory-only; treated the same as the stripped
      pattern because we only test against file paths here.

    Not supported (intentionally): negation (`!`), `**` globstar, character
    classes with locale semantics, or anchoring differences from
    `fnmatch.fnmatch` (`*` matches across `/`). Extend if the repo's
    .gitignore grows richer.
    """
    parts = rel_path.split("/")
    for raw in patterns:
        pattern = raw.lstrip("/").rstrip("/")
        if not pattern:
            continue
        if "/" in pattern:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if rel_path.startswith(prefix + "/"):
                    return True
            if rel_path.startswith(pattern + "/"):
                return True
        else:
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
    return False


class TestTestFilesLocation(unittest.TestCase):
    """
    Test-linter that enforces every `test_*.py` file to live under the
    top-level `tests/` directory.

    Files matched by `.gitignore` are skipped. The matcher is implemented
    inline (no `git` subprocess), so the lint works in environments where
    `.git/` is not mounted (e.g. the `make exec` container).
    """

    def test_no_test_files_outside_tests_dir(self):
        root = repo_root()
        patterns = _load_gitignore_patterns(root)

        offenders: list[str] = []
        for path_str in iter_project_files(extensions=(".py",)):
            if os.path.basename(path_str).startswith("test_") is False:
                continue
            path = Path(path_str)
            rel = path.relative_to(root).as_posix()
            if rel == "tests" or rel.startswith("tests/"):
                continue
            if _is_ignored(rel, patterns):
                continue
            offenders.append(rel)

        if offenders:
            self.fail(
                "Found `test_*.py` files outside the top-level `tests/` "
                "directory. Move them under `tests/` (or add them to "
                "`.gitignore` if they are not real tests):\n"
                + "\n".join(f"- {p}" for p in sorted(offenders))
            )


if __name__ == "__main__":
    unittest.main()
