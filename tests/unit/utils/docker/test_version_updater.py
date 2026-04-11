from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils.docker.version_updater import (
    latest_semver,
    update_config_versions,
)


class TestDockerVersionUpdater(unittest.TestCase):
    def test_latest_semver_respects_depth(self) -> None:
        tags = ["4", "4.5", "4.6", "4.5.1", "5"]

        self.assertEqual(latest_semver(tags, 1), "5")
        self.assertEqual(latest_semver(tags, 2), "4.6")
        self.assertEqual(latest_semver(tags, 3), "4.5.1")

    def test_update_config_versions_updates_only_target_services(self) -> None:
        original = """compose:
  services:
    moodle:
      version:            "4.5" # Keep comment
      image:              bitnamilegacy/moodle
    nginx:
      version:            alpine
      image:              nginx
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "main.yml"
            config_path.write_text(original, encoding="utf-8")

            changed = update_config_versions(config_path, {"moodle": "5.0"})

            self.assertTrue(changed)
            updated = config_path.read_text(encoding="utf-8")
            self.assertIn('version:            "5.0" # Keep comment', updated)
            self.assertIn("version:            alpine", updated)
            self.assertNotIn('version:            "4.5" # Keep comment', updated)


if __name__ == "__main__":
    unittest.main()
