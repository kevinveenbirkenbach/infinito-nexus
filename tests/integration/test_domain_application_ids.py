import os
import re
import unittest

from filter_plugins.get_all_application_ids import get_all_application_ids


def collect_domain_keys(base_dir="."):
    """
    Scan all YAML and Python files under the project for usages of domains.get('...') and domains['...']
    and return a dict mapping each domain key to a list of file:line locations where it's used.
    Ignores the integration test file itself, but will scan other test files.
    """
    pattern = re.compile(r"domains(?:\.get\(\s*['\"](?P<id>[^'\"]+)['\"]\s*\)|\[['\"](?P<id2>[^'\"]+)['\"]\])")
    locations = {}
    # Path of this test file to ignore
    ignore_path = os.path.normpath(os.path.join(base_dir, 'tests', 'integration', 'test_domain_application_ids.py'))

    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            # only scan YAML, YAML and Python files
            if not fname.endswith(('.yml', '.yaml', '.py')):
                continue
            path = os.path.normpath(os.path.join(root, fname))
            # skip this integration test file
            if path == ignore_path:
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for lineno, line in enumerate(f, start=1):
                        for m in pattern.finditer(line):
                            key = m.group('id') or m.group('id2')
                            loc = f"{path}:{lineno}"
                            locations.setdefault(key, []).append(loc)
            except (OSError, UnicodeDecodeError):
                continue
    return locations


class TestDomainApplicationIds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load valid application IDs from roles
        cls.valid_ids = set(get_all_application_ids(roles_dir='roles'))
        if not cls.valid_ids:
            raise RuntimeError("No application_ids found in roles/*/vars/main.yml")
        # Collect domain keys and their locations, excluding this test file
        cls.domain_locations = collect_domain_keys(base_dir='.')
        if not cls.domain_locations:
            raise RuntimeError("No domains.get(...) or domains[...] usages found to validate")

        # Define keys to ignore (placeholders or meta-fields)
        cls.ignore_keys = {"canonical", "aliases"}

    def test_all_keys_are_valid(self):
        """Ensure every domains.get/[] key matches a valid application_id (excluding ignored keys)."""
        def is_placeholder(key):
            # Treat keys with curly braces as placeholders
            return bool(re.match(r"^\{.+\}$", key))

        invalid = {}
        for key, locs in self.domain_locations.items():
            if key in self.ignore_keys or is_placeholder(key):
                continue
            if key not in self.valid_ids:
                invalid[key] = locs

        if invalid:
            details = []
            for key, locs in invalid.items():
                locations_str = ", ".join(locs)
                details.append(f"'{key}' at {locations_str}")
            detail_msg = "; ".join(details)
            self.fail(
                f"Found usages of domains with invalid application_ids: {detail_msg}. "
                f"Valid application_ids are: {sorted(self.valid_ids)}"
            )


if __name__ == '__main__':
    unittest.main()