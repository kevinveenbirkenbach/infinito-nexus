from __future__ import annotations

import os
import re
import subprocess
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List


OPEN_PROJECT_URL_RE = re.compile(
    r"https://open\.project\.infinito\.nexus/projects/[^/\s]+/work_packages/\d+/"
)
TODO_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(?P<body>\S.*)$")
WHITESPACE_RE = re.compile(r"\s+")

# Scan explicit marker styles that are typically used in code comments.
INLINE_TODO_RE = re.compile(
    r"(?i)(@todo\b|^\s*(?:[#/*;>]+|<!--|--)\s*(?:TODO|FIXME|HACK|XXX)\b|^\s*(?:TODO|FIXME|HACK|XXX)\b)"
)

SCANNED_SUFFIXES = {
    ".py",
    ".yml",
    ".yaml",
    ".j2",
    ".sh",
    ".js",
    ".ts",
    ".css",
    ".php",
    ".html",
    ".htm",
    ".ini",
    ".cfg",
    ".conf",
    ".toml",
    ".rst",
}

SCANNED_FILENAMES = {"Makefile", "Dockerfile"}


@dataclass(frozen=True)
class TodoFinding:
    kind: str
    path: Path
    line: int
    text: str
    link: str | None = None

    def format(self, repo_root: Path) -> str:
        rel = self.path.relative_to(repo_root).as_posix()
        normalized_text = WHITESPACE_RE.sub(" ", self.text).strip()
        rendered = f"{rel}:{self.line} - {normalized_text}"
        if self.link:
            rendered += f" -> {self.link}"
        return rendered


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tracked_files(root: Path) -> List[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.STDOUT,
        )
        rel_paths = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return [root / rel for rel in rel_paths]
    except Exception:
        return [p for p in root.rglob("*") if p.is_file()]


def is_todo_file(path: Path) -> bool:
    return path.name.lower() == "todo.md"


def should_scan_for_inline_markers(path: Path) -> bool:
    if is_todo_file(path):
        return False
    return path.suffix.lower() in SCANNED_SUFFIXES or path.name in SCANNED_FILENAMES


def scan_todo_file(path: Path) -> List[TodoFinding]:
    findings: List[TodoFinding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return findings

    for line_no, line in enumerate(lines, start=1):
        match = TODO_LIST_ITEM_RE.match(line)
        if not match:
            continue

        body = match.group("body").strip()
        if not body:
            continue

        link_match = OPEN_PROJECT_URL_RE.search(body)
        findings.append(
            TodoFinding(
                kind="todo-file",
                path=path,
                line=line_no,
                text=body,
                link=link_match.group(0) if link_match else None,
            )
        )

    return findings


def scan_inline_markers(path: Path) -> List[TodoFinding]:
    findings: List[TodoFinding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return findings

    for line_no, line in enumerate(lines, start=1):
        if INLINE_TODO_RE.search(line):
            findings.append(
                TodoFinding(
                    kind="inline-marker",
                    path=path,
                    line=line_no,
                    text=line.strip(),
                )
            )

    return findings


def emit_warning(message: str) -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        print(f"::warning::{message}")
    else:
        print(f"WARNING: {message}")


class TestTodoTransparency(unittest.TestCase):
    def test_todo_items_are_tracked_transparently(self) -> None:
        """
        TODO.md files should stay temporary thought aids.
        Keep long-lived work visible in the project backlog or in an issue.
        """
        root = repo_root()
        todo_findings: List[TodoFinding] = []
        inline_findings: List[TodoFinding] = []

        for path in tracked_files(root):
            if is_todo_file(path):
                todo_findings.extend(scan_todo_file(path))
            elif should_scan_for_inline_markers(path):
                inline_findings.extend(scan_inline_markers(path))

        unlinked_todos = [item for item in todo_findings if not item.link]

        if not unlinked_todos and not inline_findings:
            print("No unlinked TODO markers were found.")
            return

        emit_warning(
            "TODO.md files are temporary thought aids. "
            "Only TODO list items without a work-item link are reported. "
            "Link the item to "
            "https://open.project.infinito.nexus/projects/<project>/work_packages/<id>/ "
            "to suppress this warning; consider moving long-lived work to "
            "https://open.project.infinito.nexus/ or opening an issue at "
            "https://s.infinito.nexus/issues to keep the code clean."
        )

        if unlinked_todos:
            print()
            print(f"Unlinked TODO.md items ({len(unlinked_todos)}):")
            for item in unlinked_todos:
                print(f"- {item.format(root)}")

        if inline_findings:
            print()
            print(f"Inline TODO markers in code ({len(inline_findings)}):")
            for item in inline_findings:
                print(f"- {item.format(root)}")


if __name__ == "__main__":
    unittest.main()
