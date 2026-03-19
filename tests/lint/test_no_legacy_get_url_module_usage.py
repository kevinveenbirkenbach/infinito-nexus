from __future__ import annotations

import re
import unittest
from pathlib import Path


LEGACY_GET_URL_MODULE_PATTERN = re.compile(
    r"^\s*(ansible\.builtin\.get_url|get_url)\s*:\s*(?:#.*)?$"
)


class TestNoLegacyGetUrlModuleUsage(unittest.TestCase):
    REPO_ROOT = Path(__file__).resolve().parents[2]
    EXCLUDED_DIRS = {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        "__pycache__",
    }

    def _iter_yaml_files(self):
        for path in self.REPO_ROOT.rglob("*.yml"):
            rel = path.relative_to(self.REPO_ROOT)
            if any(part in self.EXCLUDED_DIRS for part in rel.parts):
                continue
            yield path

    def test_no_legacy_get_url_module_call_is_used(self):
        """
        Enforce migration from legacy get_url module calls to get_url_retry.
        """
        findings: list[tuple[str, int, str]] = []

        for yml_file in self._iter_yaml_files():
            rel = yml_file.relative_to(self.REPO_ROOT).as_posix()
            try:
                lines = yml_file.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
            except OSError:
                continue

            for line_no, line in enumerate(lines, start=1):
                if LEGACY_GET_URL_MODULE_PATTERN.match(line):
                    findings.append((rel, line_no, line.strip()))

        if findings:
            formatted = "\n".join(
                f"- {path}:{line_no}: {snippet}"
                for path, line_no, snippet in sorted(
                    findings, key=lambda item: (item[0], item[1])
                )
            )
            self.fail(
                "Found legacy get_url module calls in .yml files.\n\n"
                "Please migrate all of them to `get_url_retry:` so deploys are resilient against "
                "transient network outages.\n\n"
                f"{formatted}"
            )


if __name__ == "__main__":
    unittest.main()
