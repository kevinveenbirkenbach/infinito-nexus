import os
import sys
import re
import unittest
from cli.meta.applications.all import find_application_ids

# ensure project root is on PYTHONPATH so we can import the CLI code
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, ROOT)


class TestValidApplicationUsage(unittest.TestCase):
    """
    Integration test to ensure that only valid application IDs
    are used in all .yml, .yaml, .yml.j2, .yaml.j2, and .py files.
    Methods like applications.items() and calls to get_domain() can
    be whitelisted or validated against valid IDs.
    """

    # regex patterns to capture applications['name'], applications.get('name'), applications.name, and get_domain('name')
    APPLICATION_SUBSCRIPT_RE = re.compile(
        r"applications\[['\"](?P<name>[^'\"]+)['\"]\]"
    )
    APPLICATION_GET_RE = re.compile(
        r"applications\.get\(\s*['\"](?P<name>[^'\"]+)['\"]"
    )
    APPLICATION_ATTR_RE = re.compile(r"applications\.(?P<name>[A-Za-z_]\w*)")
    APPLICATION_DOMAIN_RE = re.compile(
        r"get_domain\(\s*['\"](?P<name>[^'\"]+)['\"]\s*\)"
    )

    # default methods and exceptions that should not be validated as application IDs
    DEFAULT_WHITELIST = {"items", "yml", "get", "values"}
    PYTHON_EXTRA_WHITELIST = {"keys"}

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

                # Whitelist je nach Dateityp erweitern
                if filename.endswith(".py"):
                    whitelist = self.DEFAULT_WHITELIST | self.PYTHON_EXTRA_WHITELIST
                else:
                    whitelist = self.DEFAULT_WHITELIST

                for pattern in (
                    self.APPLICATION_SUBSCRIPT_RE,
                    self.APPLICATION_GET_RE,
                    self.APPLICATION_ATTR_RE,
                    self.APPLICATION_DOMAIN_RE,
                ):
                    for match in pattern.finditer(content):
                        # Determine the full line containing this match
                        start = match.start()
                        line_start = content.rfind("\n", 0, start) + 1
                        line_end = content.find("\n", start)
                        line = content[
                            line_start : line_end if line_end != -1 else None
                        ]

                        # Skip any import or from-import lines
                        if line.strip().startswith(("import ", "from ")):
                            continue

                        name = match.group("name")
                        # skip whitelisted methods/exceptions
                        if name in whitelist:
                            continue
                        # each found reference must be in valid_apps
                        self.assertIn(
                            name,
                            valid_apps,
                            msg=(
                                f"{filepath}: reference to application '{name}' "
                                f"is invalid. Known IDs: {sorted(valid_apps)}"
                            ),
                        )


if __name__ == "__main__":
    unittest.main()
