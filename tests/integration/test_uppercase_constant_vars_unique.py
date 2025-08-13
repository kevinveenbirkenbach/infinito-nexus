#!/usr/bin/env python3
"""
Integration test: ensure every ALL-CAPS variable is defined only once project-wide.

Scope (by design):
- group_vars/**/*.yml
- roles/*/vars/*.yml
- roles/*/defaults/*.yml
- roles/*/defauls/*.yml   # included on purpose in case of folder typos

A variable is considered a “constant” if its key matches: ^[A-Z0-9_]+$
If a constant is declared more than once across the scanned files, the test fails
with a clear message explaining that such constants must be defined only once.
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
            # Normalize and deduplicate
            norm = os.path.normpath(path)
            if norm not in seen and os.path.isfile(norm):
                seen.add(norm)
                yield norm


def _extract_uppercase_keys_from_mapping(mapping):
    """
    Recursively extract ALL-CAPS keys from any YAML mapping.
    Returns a set of keys found in this mapping (deduplicated for the file).
    """
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                # Only consider string keys
                if isinstance(k, str) and UPPER_CONST_RE.match(k):
                    found.add(k)
                # Recurse into values to catch nested mappings too
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(mapping)
    return found


class TestUppercaseConstantVarsUnique(unittest.TestCase):
    def test_uppercase_constants_unique(self):
        # Track where each constant is defined
        constant_to_files = defaultdict(set)

        # Track YAML parse errors to fail fast with a helpful message
        parse_errors = []

        yaml_files = list(_iter_yaml_files())
        for yml in yaml_files:
            try:
                with open(yml, "r", encoding="utf-8") as f:
                    docs = list(yaml.safe_load_all(f))
            except Exception as e:
                parse_errors.append(f"{yml}: {e}")
                continue

            # Some files may be empty or contain only comments
            if not docs:
                continue

            # Collect ALL-CAPS keys for this file (dedup per file)
            file_constants = set()
            for doc in docs:
                if isinstance(doc, dict):
                    file_constants |= _extract_uppercase_keys_from_mapping(doc)
                # Non-mapping documents (e.g., lists/None) are ignored

            for const in file_constants:
                constant_to_files[const].add(yml)

        # Fail if YAML parsing had errors
        if parse_errors:
            self.fail(
                "YAML parsing failed for one or more files:\n"
                + "\n".join(f"- {err}" for err in parse_errors)
            )

        # Find duplicates (same constant in more than one file)
        duplicates = {c: sorted(files) for c, files in constant_to_files.items() if len(files) > 1}

        if duplicates:
            msg_lines = [
                "Found constants defined more than once. "
                "ALL-CAPS variables are treated as constants and must be defined only once project-wide.\n"
                "Please consolidate each duplicated constant into a single authoritative location (e.g., one vars/defaults file).",
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
