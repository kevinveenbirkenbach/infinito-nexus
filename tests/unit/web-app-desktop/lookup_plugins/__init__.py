import os
import sys
import unittest
from importlib import import_module

# Compute repo root (…/tests/unit/roles/web-app-desktop/lookup_plugins/docker_cards_grouped.py -> repo root)
_THIS_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "../../../../.."))

# Add the lookup_plugins directory to sys.path so we can import the plugin as a plain module
_LOOKUP_DIR = os.path.join(_REPO_ROOT, "roles", "web-app-desktop", "lookup_plugins")
if _LOOKUP_DIR not in sys.path:
    sys.path.insert(0, _LOOKUP_DIR)

# Import the plugin module
plugin = import_module("docker_cards_grouped")
LookupModule = plugin.LookupModule

try:
    from ansible.errors import AnsibleError
except Exception:  # Fallback for environments without full Ansible
    class AnsibleError(Exception):
        pass


class TestDockerCardsGroupedLookup(unittest.TestCase):
    def setUp(self):
        self.lookup = LookupModule()

        # Menu categories with mixed-case names to verify case-insensitive sort
        self.menu_categories = {
            "B-Group": {"tags": ["b", "beta"]},
            "a-Group": {"tags": ["a", "alpha"]},
            "Zeta": {"tags": ["z"]},
        }

        # Cards with tags; one should end up uncategorized
        self.cards = [
            {"title": "Alpha Tool", "tags": ["a"]},
            {"title": "Beta Widget", "tags": ["beta"]},
            {"title": "Zed App", "tags": ["z"]},
            {"title": "Unmatched Thing", "tags": ["x"]},
        ]

    def _run(self, cards=None, menu_categories=None):
        result = self.lookup.run(
            [cards or self.cards, menu_categories or self.menu_categories]
        )
        # Plugin returns a single-element list containing the result dict
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        return result[0]

    def test_categorization_and_uncategorized(self):
        data = self._run()
        self.assertIn("categorized", data)
        self.assertIn("uncategorized", data)

        categorized = data["categorized"]
        uncategorized = data["uncategorized"]

        # Each matching card is placed into the proper category
        self.assertIn("a-Group", categorized)
        self.assertIn("B-Group", categorized)
        self.assertIn("Zeta", categorized)

        titles_in_a = [c["title"] for c in categorized["a-Group"]]
        titles_in_b = [c["title"] for c in categorized["B-Group"]]
        titles_in_z = [c["title"] for c in categorized["Zeta"]]

        self.assertEqual(titles_in_a, ["Alpha Tool"])
        self.assertEqual(titles_in_b, ["Beta Widget"])
        self.assertEqual(titles_in_z, ["Zed App"])

        # Unmatched card should be in 'uncategorized'
        self.assertEqual(len(uncategorized), 1)
        self.assertEqual(uncategorized[0]["title"], "Unmatched Thing")

    def test_categories_sorted_alphabetically_case_insensitive(self):
        data = self._run()
        categorized = data["categorized"]

        # Verify order is alphabetical by key, case-insensitive
        keys = list(categorized.keys())
        self.assertEqual(keys, ["a-Group", "B-Group", "Zeta"])

    def test_multiple_tags_match_first_category_encountered(self):
        # A card that matches multiple categories should be placed
        # into the first matching category based on menu_categories iteration order.
        # Here "Dual Match" has both 'a' and 'b' tags; since "a-Group" is alphabetically
        # before "B-Group" only after sorting happens at RETURN time, we need to ensure the
        # assignment is based on menu_categories order (insertion order).
        menu_categories = {
            "B-Group": {"tags": ["b"]},
            "a-Group": {"tags": ["a"]},
        }
        cards = [{"title": "Dual Match", "tags": ["a", "b"]}]
        # The plugin iterates menu_categories in insertion order and breaks on first match,
        # so this card should end up in "B-Group".
        data = self._run(cards=cards, menu_categories=menu_categories)
        categorized = data["categorized"]

        self.assertIn("B-Group", categorized)
        self.assertEqual([c["title"] for c in categorized["B-Group"]], ["Dual Match"])
        self.assertNotIn("a-Group", categorized)  # no card added there

    def test_missing_arguments_raises(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run([])  # no args

        with self.assertRaises(AnsibleError):
            self.lookup.run([[]])  # only one arg


if __name__ == "__main__":
    unittest.main()
