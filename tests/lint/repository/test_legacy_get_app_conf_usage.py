"""Temporary lint sentinel for legacy get_app_conf usage in YAML/Jinja files.

Warn on every remaining occurrence under tracked repository config/template files.
Once no occurrences remain, this test must fail so the temporary sentinel itself
gets removed.
"""

from __future__ import annotations

import subprocess
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List

from utils.annotations.message import in_github_actions, warning


LEGACY_HELPER = "get_" + "app_conf"
SELF_TEST_PATH = "tests/lint/repository/test_legacy_get_app_conf_usage.py"


@dataclass(frozen=True)
class UsageFinding:
    path: Path
    line: int
    text: str

    def format(self, repo_root: Path) -> str:
        rel = self.path.relative_to(repo_root).as_posix()
        return f"{rel}:{self.line} - {self.text.strip()}"


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


def tracked_candidate_files(root: Path) -> List[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.STDOUT,
        )
        rel_paths = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        files = [root / rel for rel in rel_paths]
    except Exception:
        files = [p for p in root.rglob("*") if p.is_file()]

    results: List[Path] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel == SELF_TEST_PATH:
            continue
        results.append(path)
    return sorted(results)


def scan_file(path: Path) -> List[UsageFinding]:
    findings: List[UsageFinding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return findings

    for line_no, line in enumerate(lines, start=1):
        if LEGACY_HELPER in line:
            findings.append(UsageFinding(path=path, line=line_no, text=line))

    return findings


def emit_warning(finding: UsageFinding, root: Path) -> None:
    if not in_github_actions():
        return
    warning(
        f"Legacy {LEGACY_HELPER} usage remains.",
        title="Legacy get_app_conf usage",
        file=finding.path.relative_to(root).as_posix(),
        line=finding.line,
    )


class TestLegacyGetAppConfUsage(unittest.TestCase):
    def test_warn_until_last_legacy_usage_is_removed(self) -> None:
        root = repo_root()
        candidates = tracked_candidate_files(root)
        self.assertTrue(
            candidates,
            "No tracked repository files found.",
        )

        findings: List[UsageFinding] = []
        for path in candidates:
            findings.extend(scan_file(path))

        findings.sort(key=lambda item: (item.path.as_posix(), item.line))

        if not findings:
            self.fail(
                "No legacy get_app_conf usages remain in tracked repository files.\n"
                "This temporary lint test can be removed:\n"
                f"- {SELF_TEST_PATH}"
            )

        for item in findings:
            emit_warning(item, root)

        if not in_github_actions():
            print()
            print(
                f"[WARNING] Remaining legacy {LEGACY_HELPER} usages ({len(findings)}):"
            )
            for item in findings:
                print(f"- {item.format(root)}")


if __name__ == "__main__":
    unittest.main()
