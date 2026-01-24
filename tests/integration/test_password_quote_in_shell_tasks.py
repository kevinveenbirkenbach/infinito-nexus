# tests/integration/test_password_quote_in_shell_tasks.py
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


JINJA_EXPR_RE = re.compile(r"{{(.*?)}}", re.DOTALL)
PASSWORD_TOKEN_RE = re.compile(r"(?i)\b[a-z0-9_]*password[a-z0-9_]*\b")
QUOTE_FILTER_RE = re.compile(r"\|\s*quote\b", re.IGNORECASE)

SHELL_KEY_RE = re.compile(r"^\s*(?:ansible\.builtin\.)?shell\s*:\s*(.*)$")


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


def _indent_level(s: str) -> int:
    return len(s) - len(s.lstrip(" "))


def _collect_shell_blocks(text: str) -> List[tuple[int, str]]:
    """
    Return list of (start_line_no, block_text) for each shell: block.
    Best-effort indentation-based collector (no YAML parsing).
    """
    lines = text.splitlines()
    blocks: List[tuple[int, str]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        m = SHELL_KEY_RE.match(line)
        if not m:
            i += 1
            continue

        start_line_no = i + 1
        base_indent = _indent_level(line)

        collected = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]

            # Keep blank lines inside the block
            if nxt.strip() == "":
                collected.append(nxt)
                i += 1
                continue

            # Stop when indentation returns to base or less (next YAML key/item)
            if _indent_level(nxt) <= base_indent:
                break

            collected.append(nxt)
            i += 1

        blocks.append((start_line_no, "\n".join(collected)))

    return blocks


def _scan_shell_block(file_path: Path, start_line: int, block: str) -> List[Finding]:
    findings: List[Finding] = []

    for m in JINJA_EXPR_RE.finditer(block):
        expr = (m.group(1) or "").strip()
        if not PASSWORD_TOKEN_RE.search(expr):
            continue
        if QUOTE_FILTER_RE.search(expr):
            continue

        # Approximate line number within block
        rel_line = block.count("\n", 0, m.start())
        line_no = start_line + rel_line

        snippet = "{{ " + " ".join(expr.split()) + " }}"
        findings.append(
            Finding(
                file=file_path,
                line=line_no,
                reason="In shell tasks, password expressions must include '| quote'",
                snippet=snippet,
            )
        )

    return findings


class TestPasswordQuoteInShellTasks(unittest.TestCase):
    def test_passwords_are_quoted_in_shell_tasks(self) -> None:
        repo_root = (
            Path(__file__).resolve().parents[2]
        )  # tests/integration/ -> repo root

        all_findings: List[Finding] = []
        for yml in _iter_roles_yml_files(repo_root):
            text = yml.read_text(encoding="utf-8", errors="replace")
            for start_line, block in _collect_shell_blocks(text):
                all_findings.extend(_scan_shell_block(yml, start_line, block))

        if all_findings:
            msg = "\n".join(f.format() for f in all_findings)
            self.fail(
                "Violations found (password outputs in shell tasks must use '| quote'):\n"
                f"{msg}\n"
            )


if __name__ == "__main__":
    unittest.main()
