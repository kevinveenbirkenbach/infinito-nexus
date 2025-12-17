import unittest
from pathlib import Path
import re
import sys
from filter_plugins.invokable_paths import get_invokable_paths

# Ensure your project root is on PYTHONPATH so filter_plugins can be imported
ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

STAGES_DIR = ROOT / "tasks" / "stages"
GROUPS_DIR = ROOT / "tasks" / "groups"

class TestMetaRolesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the filter directly
        cls.role_files = get_invokable_paths(suffix="-roles.yml")
        cls.invokable_items = get_invokable_paths()

        # Read all playbook YAML contents under tasks/stages
        cls.playbook_contents = {}
        for path in STAGES_DIR.rglob("*.yml"):
            cls.playbook_contents[path] = path.read_text(encoding="utf-8")

        # Regex for include_tasks line with {{ item }}-roles.yml
        cls.include_pattern = re.compile(
            r'include_tasks:\s*["\']\./tasks/groups/\{\{\s*item\s*\}\}-roles\.yml["\']'
        )

    def test_all_role_files_exist(self):
        """Each '-roles.yml' path returned by the filter must exist in the project root."""
        missing = []
        for fname in self.role_files:
            path = GROUPS_DIR / fname
            if not path.is_file():
                missing.append(fname)
        self.assertFalse(
            missing,
            f"The following role files are missing at project root: {missing}"
        )

    def test_each_invokable_item_referenced_in_playbooks(self):
        """
        Each invokable item (without suffix) must be looped through in at least one playbook
        and include its corresponding include_tasks entry.
        """
        not_referenced = []
        for item in self.invokable_items:
            found = False
            loop_entry = re.compile(rf"-\s*{re.escape(item)}\b")
            for content in self.playbook_contents.values():
                if self.include_pattern.search(content) and loop_entry.search(content):
                    found = True
                    break
            if not found:
                not_referenced.append(item)

        self.assertEqual(
            not_referenced, [],
            f"The following invokable items are not referenced in any playbook: {not_referenced}"
        )

if __name__ == "__main__":
    unittest.main()
