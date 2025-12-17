import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")),
)

from filter_plugins.redirect_filters import FilterModule


class TestAddRedirectIfGroup(unittest.TestCase):
    """Unit-tests for the add_redirect_if_group filter."""

    def setUp(self):
        # Obtain the callable once for reuse
        self.add_redirect = FilterModule().filters()["add_redirect_if_group"]

    def test_appends_redirect_when_group_present(self):
        original = [{"source": "a", "target": "b"}]
        result = self.add_redirect(
            original,
            group="lam",
            source="ldap.example.com",
            target="lam.example.com",
            group_names=["lam", "other"],
        )

        # Original list must stay unchanged
        self.assertEqual(len(original), 1)
        # Result list must contain the extra entry
        self.assertEqual(len(result), 2)
        self.assertIn(
            {"source": "ldap.example.com", "target": "lam.example.com"}, result
        )

    def test_keeps_list_unchanged_when_group_absent(self):
        original = [{"source": "a", "target": "b"}]
        result = self.add_redirect(
            original,
            group="lam",
            source="ldap.example.com",
            target="lam.example.com",
            group_names=["unrelated"],
        )

        # No new entries
        self.assertEqual(result, original)
        # But ensure a new list object was returned (no in-place mutation)
        self.assertIsNot(result, original)


if __name__ == "__main__":
    unittest.main()
