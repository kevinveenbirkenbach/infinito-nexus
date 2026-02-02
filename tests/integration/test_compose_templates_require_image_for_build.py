# tests/integration/test_compose_templates_require_image_for_build.py
#
# Integration test:
# Ensures that every docker-compose template/file that contains a `build:` mapping
# also contains an `image:` key on the same indentation level (same YAML mapping level).
#
# Checked files:
#   - roles/*/templates/docker-compose.yml.j2
#   - roles/*/files/docker-compose.yml
#
# Rationale:
# Your CA-injection logic (and other tooling) may need a stable image name to inspect
# entrypoint/cmd. Compose allows build without image, but then image names are not stable.

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


BUILD_RE = re.compile(r"^(?P<indent>[ \t]*)build:\s*(#.*)?$")
IMAGE_RE = re.compile(r"^(?P<indent>[ \t]*)image:\s*(?P<rest>.+)?$")
COMMENTED_RE = re.compile(r"^\s*#")
BLANK_RE = re.compile(r"^\s*$")


@dataclass
class Finding:
    file: str
    build_line: int
    build_indent: int
    note: str


def _repo_root_from_test_file(test_file: str) -> Path:
    """
    Compute repo root from this test file location.
    tests/integration/<this_file> -> repo root is parents[2]
    """
    p = Path(test_file).resolve()
    # .../tests/integration/test_*.py
    return p.parents[2]


def _is_ignored_line(line: str) -> bool:
    return bool(BLANK_RE.match(line) or COMMENTED_RE.match(line))


def _indent_len(indent: str) -> int:
    # Tabs are allowed in regex, but we treat them as 1 unit here.
    # If you enforce spaces-only, this still works.
    return len(indent.replace("\t", " "))


def _block_bounds_for_key(
    lines: List[str], idx: int, key_indent_len: int
) -> Tuple[int, int]:
    """
    Determine bounds of the YAML mapping block that contains the key at lines[idx],
    based on indentation dropping below key_indent_len.
    Returns (start_inclusive, end_exclusive).
    """
    # Scan upwards to find where indentation drops below key_indent_len.
    start = idx
    j = idx - 1
    while j >= 0:
        ln = lines[j]
        if _is_ignored_line(ln):
            j -= 1
            continue

        # Indentation of this non-empty, non-comment line
        cur_indent = len(ln) - len(ln.lstrip(" \t"))
        cur_indent_len = _indent_len(ln[:cur_indent])

        if cur_indent_len < key_indent_len:
            break
        start = j
        j -= 1

    # Scan downwards similarly
    end = idx + 1
    k = idx + 1
    while k < len(lines):
        ln = lines[k]
        if _is_ignored_line(ln):
            k += 1
            end = k
            continue

        cur_indent = len(ln) - len(ln.lstrip(" \t"))
        cur_indent_len = _indent_len(ln[:cur_indent])

        if cur_indent_len < key_indent_len:
            break
        k += 1
        end = k

    return start, end


def _has_image_same_indent(
    lines: List[str], start: int, end: int, indent_str: str
) -> bool:
    """
    Check if an `image:` key exists at the same indent (exact prefix match) within [start, end).
    """
    needle = f"{indent_str}image:"
    for i in range(start, end):
        ln = lines[i]
        if _is_ignored_line(ln):
            continue
        # Must match exact indent string + "image:" (same mapping level)
        if ln.startswith(needle):
            # also ensure it's not commented (already handled) and looks like a key
            return True
    return False


def _scan_file_for_missing_image(path: Path) -> List[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    findings: List[Finding] = []

    for idx, ln in enumerate(lines):
        if _is_ignored_line(ln):
            continue

        m = BUILD_RE.match(ln)
        if not m:
            continue

        indent_str = m.group("indent") or ""
        indent_len = _indent_len(indent_str)

        # Determine block bounds for this build: key
        b_start, b_end = _block_bounds_for_key(lines, idx, indent_len)

        # Need image: at same indent level somewhere within that block
        if not _has_image_same_indent(lines, b_start, b_end, indent_str):
            findings.append(
                Finding(
                    file=str(path),
                    build_line=idx + 1,  # 1-based for humans
                    build_indent=indent_len,
                    note="Found `build:` without `image:` at the same indentation level in the same mapping block.",
                )
            )

    return findings


class TestComposeBuildRequiresImage(unittest.TestCase):
    def test_all_compose_templates_and_files_have_image_for_build(self) -> None:
        repo_root = _repo_root_from_test_file(__file__)
        roles_dir = repo_root / "roles"

        patterns = [
            "*/templates/docker-compose.yml.j2",
            "*/files/docker-compose.yml",
        ]

        targets: List[Path] = []
        for pat in patterns:
            targets.extend(sorted(roles_dir.glob(pat)))

        self.assertTrue(
            targets,
            f"No compose templates/files found under {roles_dir} for patterns: {patterns}",
        )

        all_findings: List[Finding] = []
        for f in targets:
            all_findings.extend(_scan_file_for_missing_image(f))

        if all_findings:
            # Pretty error output
            msg_lines = [
                "Some docker-compose templates/files contain a `build:` key but are missing an `image:` key "
                "at the same indentation level (same YAML mapping level).",
                "",
                "Offenders:",
            ]
            for it in all_findings:
                msg_lines.append(
                    f"- {it.file}:{it.build_line} (build indent={it.build_indent}) -> {it.note}"
                )
            msg_lines.append("")
            msg_lines.append(
                "Fix: for each service that has `build:`, add a stable `image:` name on the same level, e.g."
            )
            msg_lines.append("  service:")
            msg_lines.append("    image: myorg/myimage:local")
            msg_lines.append("    build:")
            msg_lines.append("      context: .")
            self.fail("\n".join(msg_lines))


if __name__ == "__main__":
    unittest.main()
