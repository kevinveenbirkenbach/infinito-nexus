# tests/integration/test_password_no_quote_in_definitions.py
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


QUOTE_FILTER_RE = re.compile(r"\|\s*quote\b", re.IGNORECASE)

# YAML "definition" line where the KEY contains "password" (case-insensitive)
# Examples:
#   db_password: "{{ vault_db_password }}"
#   PASSWORD: somevalue
PASSWORD_KEY_LINE_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z0-9_.-]*password[A-Za-z0-9_.-]*)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    file: Path
    line: int
    reason: str
    snippet: str

    def format(self) -> str:
        return f"{self.file.as_posix()}:{self.line}: {self.reason}: {self.snippet}"


def _iter_roles_yml_files(repo_root: Path) -> Iterable[Path]:
    roles_dir = repo_root / "roles"
    if not roles_dir.is_dir():
        return []
    return roles_dir.rglob("*.yml")


def _scan_file(path: Path) -> List[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: List[Finding] = []

    for idx, line in enumerate(text.splitlines(), start=1):
        m = PASSWORD_KEY_LINE_RE.match(line)
        if not m:
            continue

        value = m.group("value") or ""
        if QUOTE_FILTER_RE.search(value):
            findings.append(
                Finding(
                    file=path,
                    line=idx,
                    reason="Password variable definition must NOT use '| quote' in its value",
                    snippet=line.strip(),
                )
            )

    return findings


class TestPasswordDefinitionsNoQuote(unittest.TestCase):
    def test_password_definitions_must_not_use_quote_filter(self) -> None:
        repo_root = (
            Path(__file__).resolve().parents[2]
        )  # tests/integration/ -> repo root

        all_findings: List[Finding] = []
        for yml in _iter_roles_yml_files(repo_root):
            all_findings.extend(_scan_file(yml))

        if all_findings:
            msg = "\n".join(f.format() for f in all_findings)
            self.fail(
                "Violations found (password definitions must not use '| quote'):\n"
                f"{msg}\n"
            )


if __name__ == "__main__":
    unittest.main()
