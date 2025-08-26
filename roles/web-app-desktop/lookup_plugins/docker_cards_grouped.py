from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        """
        Group the given cards into categorized and uncategorized lists
        based on the tags from menu_categories.
        """
        if len(terms) < 2:
            raise AnsibleError("Missing required arguments")

        cards = terms[0]
        menu_categories = terms[1]

        categorized = {}
        uncategorized = []

        for card in cards:
            found = False
            for category, data in menu_categories.items():
                if any(tag in data.get('tags', []) for tag in card.get('tags', [])):
                    categorized.setdefault(category, []).append(card)
                    found = True
                    break
            if not found:
                uncategorized.append(card)

        return [
            {
                'categorized': categorized,
                'uncategorized': uncategorized,
            }
        ]

