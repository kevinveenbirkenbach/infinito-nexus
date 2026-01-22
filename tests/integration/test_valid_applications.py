import os
import sys
import re
from typing import Optional
import unittest

# ensure project root is on PYTHONPATH so we can import the CLI code
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, ROOT)

from cli.meta.applications.all import find_application_ids  # noqa: E402


class TestValidApplicationUsage(unittest.TestCase):
    """
    Integration test to ensure that only valid application IDs
    are used in all .yml, .yaml, .yml.j2, .yaml.j2, and .py files.

    It detects:
    - applications['name']
    - applications.get('name')
    - applications.name
    - get_domain('name')

    For Python, it avoids false positives like applications.setdefault(...),
    by skipping attribute matches that are immediately used as a call.
    """

    # regex patterns to capture applications['name'], applications.get('name'), applications.name, and get_domain('name')
    APPLICATION_SUBSCRIPT_RE = re.compile(
        r"applications\[['\"](?P<name>[^'\"]+)['\"]\]"
    )
    APPLICATION_GET_RE = re.compile(
        r"applications\.get\(\s*['\"](?P<name>[^'\"]+)['\"]"
    )
    APPLICATION_ATTR_RE = re.compile(r"(?<!\.)applications\.(?P<name>[A-Za-z_]\w*)")
    APPLICATION_DOMAIN_RE = re.compile(
        r"get_domain\(\s*['\"](?P<name>[^'\"]+)['\"]\s*\)"
    )

    # default methods and exceptions that should not be validated as application IDs
    DEFAULT_WHITELIST = {"items", "yml", "get", "values"}
    PYTHON_EXTRA_WHITELIST = {"keys"}

    @staticmethod
    def _line_no_and_col(content: str, index: int) -> tuple[int, int]:
        """
        Return 1-based (line_no, col) for a 0-based absolute index into content.
        """
        line_no = content.count("\n", 0, index) + 1
        line_start = content.rfind("\n", 0, index) + 1
        col = (index - line_start) + 1
        return line_no, col

    @staticmethod
    def _next_non_ws_char(content: str, index: int) -> Optional[str]:
        """
        Return the next non-whitespace character after index, or None if EOF.
        """
        while index < len(content) and content[index].isspace():
            index += 1
        return content[index] if index < len(content) else None

    def test_application_references_use_valid_ids(self):
        valid_apps = find_application_ids()

        tests_dir = os.path.join(ROOT, "tests")
        for dirpath, _, filenames in os.walk(ROOT):
            # skip the tests/ directory and all its subdirectories
            if dirpath == tests_dir or dirpath.startswith(tests_dir + os.sep):
                continue

            for filename in filenames:
                if not filename.lower().endswith(
                    (".yml", ".yaml", ".yml.j2", ".yaml.j2", ".py")
                ):
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    # skip files that cannot be opened
                    continue

                # Extend whitelist depending on file type
                if filename.endswith(".py"):
                    whitelist = self.DEFAULT_WHITELIST | self.PYTHON_EXTRA_WHITELIST
                else:
                    whitelist = self.DEFAULT_WHITELIST

                patterns = (
                    self.APPLICATION_SUBSCRIPT_RE,
                    self.APPLICATION_GET_RE,
                    self.APPLICATION_ATTR_RE,
                    self.APPLICATION_DOMAIN_RE,
                )

                for pattern in patterns:
                    for match in pattern.finditer(content):
                        start = match.start()

                        # Determine the full line containing this match
                        line_start = content.rfind("\n", 0, start) + 1
                        line_end = content.find("\n", start)
                        line = content[
                            line_start : line_end if line_end != -1 else None
                        ]

                        # Skip any import or from-import lines
                        if line.strip().startswith(("import ", "from ")):
                            continue

                        name = match.group("name")

                        # In Python: avoid false positives like applications.setdefault(...)
                        # APPLICATION_ATTR_RE matches dict methods too.
                        # If it is used as a call (applications.<name>(...)), skip it.
                        if (
                            filename.endswith(".py")
                            and pattern is self.APPLICATION_ATTR_RE
                        ):
                            nxt = self._next_non_ws_char(content, match.end())
                            if nxt == "(":
                                continue

                        # skip whitelisted methods/exceptions
                        if name in whitelist:
                            continue

                        line_no, col = self._line_no_and_col(content, start)

                        # each found reference must be in valid_apps
                        self.assertIn(
                            name,
                            valid_apps,
                            msg=(
                                f"{filepath}: reference to application '{name}' is invalid.\n"
                                f"Location: line {line_no}, col {col}\n"
                                f"Line: {line.rstrip()}\n"
                                f"Known IDs: {sorted(valid_apps)}"
                            ),
                        )


if __name__ == "__main__":
    unittest.main()
