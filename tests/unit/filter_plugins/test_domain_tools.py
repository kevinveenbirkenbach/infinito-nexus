import os
import sys
import unittest

# Make project root importable so "filter_plugins.domain_tools" works no matter where tests run from
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ansible.errors import AnsibleFilterError  # noqa: E402
from filter_plugins.domain_tools import to_zone, FilterModule  # noqa: E402


class TestDomainTools(unittest.TestCase):
    def test_to_zone_basic(self):
        self.assertEqual(to_zone("example.com"), "example.com")
        self.assertEqual(to_zone("mail.example.com"), "example.com")
        self.assertEqual(to_zone("a.b.c.example.com"), "example.com")

    def test_to_zone_trailing_and_leading_dots(self):
        self.assertEqual(to_zone("example.com."), "example.com")
        self.assertEqual(to_zone(".mail.example.com."), "example.com")

    def test_to_zone_keeps_two_last_labels(self):
        # Naive behavior by design: last two labels only
        self.assertEqual(to_zone("service.co.uk"), "co.uk")
        self.assertEqual(to_zone("mx.mail.service.co.uk"), "co.uk")
        self.assertEqual(to_zone("uni.edu.pl"), "edu.pl")

    def test_to_zone_invalid_inputs(self):
        with self.assertRaises(AnsibleFilterError):
            to_zone("")  # empty
        with self.assertRaises(AnsibleFilterError):
            to_zone("   ")  # whitespace
        with self.assertRaises(AnsibleFilterError):
            to_zone("localhost")  # no TLD part
        with self.assertRaises(AnsibleFilterError):
            to_zone(None)  # type: ignore

    def test_filtermodule_exports(self):
        fm = FilterModule()
        filters = fm.filters()
        self.assertIn("to_zone", filters)
        self.assertIs(filters["to_zone"], to_zone)


if __name__ == "__main__":
    unittest.main()
