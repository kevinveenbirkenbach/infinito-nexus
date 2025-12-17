# tests/integration/test_no_applications_variable_usage.py

import os
import re
import unittest


class TestNoApplicationsVariableUsage(unittest.TestCase):
    """
    This test ensures that the pattern `applications[some_variable]` is not used anywhere
    under the roles/ directory. Instead, the usage of get_app_conf should be preferred.
    """

    APPLICATIONS_VARIABLE_PATTERN = re.compile(
        r"applications\[\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\]"
    )

    def test_no_applications_variable_usage(self):
        roles_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "roles")
        )
        found = []

        for root, dirs, files in os.walk(roles_dir):
            # Skip __pycache__ folders
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                file_path = os.path.join(root, file)
                # Skip this test file itself (so it can contain the pattern in docstrings)
                if os.path.abspath(file_path) == os.path.abspath(__file__):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for lineno, line in enumerate(f, 1):
                            match = self.APPLICATIONS_VARIABLE_PATTERN.search(line)
                            if match:
                                found.append(f"{file_path}:{lineno}: {line.strip()}")
                except Exception:
                    # Binary or unreadable file, skip
                    continue

        if found:
            self.fail(
                "Found illegal usages of 'applications[variable]' in the following locations:\n"
                + "\n".join(found)
                + "\n\nPlease use get_app_conf instead."
            )


if __name__ == "__main__":
    unittest.main()
