# tests/unit/filter_plugins/test_active_docker.py
import os
import sys
import unittest
from pathlib import Path

# Ensure repository root is on sys.path so "filter_plugins" can be imported
ROOT = Path(__file__).resolve().parents[3]  # .../tests/unit/filter_plugins -> repo root
sys.path.insert(0, str(ROOT))

from filter_plugins.active_docker import (
    active_docker_container_count,
    FilterModule,
)


class TestActiveDockerFilter(unittest.TestCase):
    def setUp(self):
        # default group_names simulating current host membership
        self.group_names = [
            "web-app-jira",
            "web-app-confluence",
            "svc-db-postgres",
            "svc-ai-ollama",
            "web-svc-cdn",
            "unrelated-group",
        ]

        # a representative applications structure
        self.apps = {
            # counted (prefix web-/svc- AND in group_names)
            "web-app-jira": {
                "docker": {
                    "services": {
                        "jira": {"enabled": True},
                        "proxy": {},  # enabled undefined -> counts
                        "debug": {"enabled": False},  # should NOT count
                    }
                }
            },
            "web-app-confluence": {
                "docker": {
                    "services": {
                        "confluence": {"enabled": True},
                    }
                }
            },
            "svc-db-postgres": {
                "docker": {
                    "services": {
                        "postgres": {"enabled": True},
                        "backup": {"enabled": False},  # no
                    }
                }
            },
            "svc-ai-ollama": {
                "docker": {
                    "services": {
                        # non-dict service cfg (string) -> should count as "enabled"
                        "ollama": "ghcr.io/ollama/ollama:latest",
                    }
                }
            },
            "web-svc-cdn": {
                "docker": {
                    "services": {
                        # weird truthy value -> treated as enabled
                        "cdn": {"enabled": "yes"},
                    }
                }
            },

            # NOT counted: wrong prefix
            "db-core-mariadb": {
                "docker": {"services": {"mariadb": {"enabled": True}}}
            },
            # NOT counted: not in group_names
            "web-app-gitlab": {
                "docker": {"services": {"gitlab": {"enabled": True}}}
            },
            # NOT counted: missing docker/services
            "web-app-empty": {},
        }

    def test_basic_count(self):
        # Expected counted services:
        # web-app-jira: jira(True) + proxy(undefined) = 2
        # web-app-confluence: confluence(True) = 1
        # svc-db-postgres: postgres(True) = 1
        # svc-ai-ollama: ollama(string) = 1
        # web-svc-cdn: cdn("yes") -> truthy = 1
        # Total = 6
        cnt = active_docker_container_count(self.apps, self.group_names)
        self.assertEqual(cnt, 6)

    def test_filter_module_registration(self):
        fm = FilterModule().filters()
        self.assertIn("active_docker_container_count", fm)
        cnt = fm["active_docker_container_count"](self.apps, self.group_names)
        self.assertEqual(cnt, 6)

    def test_prefix_regex_override(self):
        # Only count svc-* prefixed apps in group_names
        cnt = active_docker_container_count(
            self.apps, self.group_names, prefix_regex=r"^svc-.*"
        )
        # svc-db-postgres (1) + svc-ai-ollama (1) = 2
        self.assertEqual(cnt, 2)

    def test_not_in_group_names_excluded(self):
        # Add a matching app but omit from group_names → should not count
        apps = dict(self.apps)
        apps["web-app-pixelfed"] = {"docker": {"services": {"pix": {"enabled": True}}}}
        cnt = active_docker_container_count(apps, self.group_names)
        # stays 6
        self.assertEqual(cnt, 6)

    def test_missing_services_and_non_mapping(self):
        # If applications is not a mapping, returns 0/1 based on ensure_min_one
        self.assertEqual(active_docker_container_count(None, self.group_names), 0)
        self.assertEqual(
            active_docker_container_count(None, self.group_names, ensure_min_one=True),
            1,
        )

        # App with no docker/services should be ignored (already in fixture)
        cnt = active_docker_container_count(self.apps, self.group_names)
        self.assertEqual(cnt, 6)

    def test_enabled_false_excluded(self):
        # Ensure explicit false is excluded
        apps = dict(self.apps)
        apps["web-app-jira"]["docker"]["services"]["only_false"] = {"enabled": False}
        cnt = active_docker_container_count(apps, self.group_names)
        self.assertEqual(cnt, 6)  # unchanged

    def test_enabled_truthy_string_included(self):
        # Already covered by web-svc-cdn ("yes"), but verify explicitly
        apps = dict(self.apps)
        apps["web-app-confluence"]["docker"]["services"]["extra"] = {"enabled": "true"}
        cnt = active_docker_container_count(apps, self.group_names)
        self.assertEqual(cnt, 7)

    def test_ensure_min_one(self):
        # Construct inputs that produce zero
        apps = {
            "web-app-foo": {"docker": {"services": {"s": {"enabled": False}}}},
        }
        cnt0 = active_docker_container_count(apps, ["web-app-foo"])
        cnt1 = active_docker_container_count(
            apps, ["web-app-foo"], ensure_min_one=True
        )
        self.assertEqual(cnt0, 0)
        self.assertEqual(cnt1, 1)


if __name__ == "__main__":
    unittest.main()
