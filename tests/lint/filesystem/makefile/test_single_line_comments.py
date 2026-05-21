"""Makefile target definitions: at most one `# ...` comment line directly above each target."""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils.cache.files import read_text

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

_TARGET_RE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9_-]*)\s*:")
_COMMENT_RE = re.compile(r"^\s*#")
# nocheck:foo markers are suppression directives, not WHY comments.
_NOCHECK_RE = re.compile(r"^\s*#\s*nocheck\s*:")


@dataclass(frozen=True)
class _Violation:
    line_no: int
    target: str
    comment_lines: int


def _comments_directly_above(lines: list[str], target_idx: int) -> int:
    """Count consecutive `#`-prefixed lines directly above index *target_idx*
    (no blank line between). `# nocheck:` suppression markers do not count."""
    count = 0
    cursor = target_idx - 1
    while cursor >= 0:
        line = lines[cursor]
        if _COMMENT_RE.match(line):
            if not _NOCHECK_RE.match(line):
                count += 1
            cursor -= 1
            continue
        break
    return count


def _scan_file(path: Path) -> list[_Violation]:
    lines = read_text(str(path)).splitlines()
    out: list[_Violation] = []
    for index, line in enumerate(lines):
        match = _TARGET_RE.match(line)
        if match is None:
            continue
        n = _comments_directly_above(lines, index)
        if n > 1:
            out.append(_Violation(index + 1, match.group("name"), n))
    return out


class TestMakefileSingleLineComments(unittest.TestCase):
    def test_makefile_targets_have_at_most_one_comment_line_above(self) -> None:
        path = PROJECT_ROOT / "Makefile"
        self.assertTrue(path.is_file(), "Makefile not found at project root")

        violations = _scan_file(path)
        if not violations:
            return

        lines = [
            f"Makefile targets with multi-line comment block "
            f"({len(violations)} violations):",
            "",
            "Makefile targets must be preceded by AT MOST one `# ...` comment line "
            "on the immediately preceding line. Collapse multi-line blocks to a "
            "single one-line WHY comment.",
            "",
            "Offenders:",
        ]
        lines.extend(
            f"  Makefile:{v.line_no} ({v.target}): {v.comment_lines} comment lines above"
            for v in violations
        )
        self.fail("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
