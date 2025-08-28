#!/usr/bin/env python3
"""
Integration test: ensure every TOP-LEVEL ALL-CAPS variable is defined only once project-wide.

Scope (by design):
- group_vars/**/*.yml
- roles/*/vars/*.yml
- roles/*/defaults/*.yml
- roles/*/defauls/*.yml   # included on purpose in case of folder typos

A variable is considered a “constant” if its KEY (at the top level of a YAML document)
matches: ^[A-Z0-9_]+$

Only TOP-LEVEL keys are checked for uniqueness. Nested keys are ignored to allow
namespacing like DICTIONARYA.ENTRY and DICTIONARYB.ENTRY without conflicts.
"""

import os
import glob
import unittest
import re
from collections import defaultdict

try:
    import yaml
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required for this test. Install with: pip install pyyaml"
    ) from e


UPPER_CONST_RE = re.compile(r"^[A-Z0-9_]+$")


def _iter_yaml_files():
    """Yield all YAML file paths in the intended scope."""
    patterns = [
        os.path.join("group_vars", "**", "*.yml"),
        os.path.join("roles", "*", "vars", "*.yml"),
        os.path.join("roles", "*", "defaults", "*.yml"),
        os.path.join("roles", "*", "defauls", "*.yml"),  # intentionally included
    ]
    seen = set()
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            norm = os.path.normpath(path)
            if norm not in seen and os.path.isfile(norm):
                seen.add(norm)
                yield norm


def _extract_top_level_uppercase_keys(docs):
    """
    Return a set of TOP-LEVEL ALL-CAPS keys found across all mapping documents in a file.
    Nested keys are intentionally ignored.
    """
    found = set()
    for doc in docs:
        if isinstance(doc, dict):
            for k in doc.keys():
                if isinstance(k, str) and UPPER_CONST_RE.match(k):
                    found.add(k)
    return found


class TestUppercaseConstantVarsUnique(unittest.TestCase):
    def test_uppercase_constants_unique(self):
        # Track where each TOP-LEVEL constant is defined
        constant_to_files = defaultdict(set)

        # Track YAML parse errors to fail with a helpful message
        parse_errors = []

        yaml_files = list(_iter_yaml_files())
        for yml in yaml_files:
            try:
                with open(yml, "r", encoding="utf-8") as f:
                    docs = list(yaml.safe_load_all(f))
            except Exception as e:
                parse_errors.append(f"{yml}: {e}")
                continue

            if not docs:
                continue

            file_constants = _extract_top_level_uppercase_keys(docs)

            for const in file_constants:
                constant_to_files[const].add(yml)

        if parse_errors:
            self.fail(
                "YAML parsing failed for one or more files:\n"
                + "\n".join(f"- {err}" for err in parse_errors)
            )

        # Duplicates are same TOP-LEVEL constant appearing in >1 files
        duplicates = {
            c: sorted(files)
            for c, files in constant_to_files.items()
            if len(files) > 1
        }

        if duplicates:
            msg_lines = [
                "Found TOP-LEVEL constants defined more than once. "
                "ALL-CAPS top-level variables are treated as constants and must be defined only once project-wide.\n"
                "Nested ALL-CAPS keys are allowed and ignored by this test.",
                "",
            ]
            for const, files in sorted(duplicates.items()):
                msg_lines.append(f"* {const} defined in {len(files)} files:")
                for f in files:
                    msg_lines.append(f"    - {f}")
                msg_lines.append("")  # spacer
            self.fail("\n".join(msg_lines))


if __name__ == "__main__":
    unittest.main()
