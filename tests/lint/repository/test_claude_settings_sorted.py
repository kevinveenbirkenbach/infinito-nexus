import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"

SORTED_ARRAYS: list[tuple[str, ...]] = [
    ("permissions", "allow"),
    ("permissions", "deny"),
    ("permissions", "ask"),
    ("sandbox", "network", "allowedDomains"),
    ("sandbox", "filesystem", "allowWrite"),
    ("sandbox", "filesystem", "denyRead"),
]


class TestClaudeSettingsSorted(unittest.TestCase):
    """Lint .claude/settings.json: every list-of-strings array we curate by hand
    must stay ASCII-sorted so diffs are reviewable and merge conflicts minimal."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(SETTINGS_PATH) as fh:
            cls.settings = json.load(fh)

    def test_arrays_are_ascending(self) -> None:
        for path in SORTED_ARRAYS:
            label = ".".join(path)
            with self.subTest(array=label):
                obj = self.settings
                for key in path:
                    obj = obj[key]
                self.assertEqual(
                    obj,
                    sorted(obj),
                    f"{label} is not ASCII-sorted ascending in {SETTINGS_PATH}",
                )


if __name__ == "__main__":
    unittest.main()
