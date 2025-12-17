import os
import re
import unittest
from filter_plugins.get_all_application_ids import get_all_application_ids
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class TestGetDomainApplicationIds(unittest.TestCase):
    """
    Integration test to verify that all string literals passed to get_domain()
    correspond to valid application_id values defined in roles/*/vars/main.yml.
    """

    GET_DOMAIN_PATTERN = re.compile(r"get_domain\(\s*['\"]([^'\"]+)['\"]\s*\)")

    def test_get_domain_literals_are_valid_ids(self):
        # Collect all application IDs from roles
        valid_ids = set(get_all_application_ids())

        # Walk through project files
        invalid_usages = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Skip tests directory to avoid matching in test code
            if 'tests' in root.split(os.sep):
                continue
            for fname in files:
                if not fname.endswith('.py'):
                    continue
                path = os.path.join(root, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for match in self.GET_DOMAIN_PATTERN.finditer(content):
                    literal = match.group(1)
                    if literal not in valid_ids:
                        invalid_usages.append((path, literal))

        if invalid_usages:
            msgs = [f"{path}: '{lit}' is not a valid application_id" for path, lit in invalid_usages]
            self.fail("Found invalid get_domain() usages:\n" + "\n".join(msgs))

if __name__ == '__main__':
    unittest.main()
