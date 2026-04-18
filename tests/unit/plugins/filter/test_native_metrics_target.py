from __future__ import annotations

import unittest
from unittest.mock import patch

from ansible.errors import AnsibleFilterError

from plugins.filter.native_metrics_target import native_metrics_target


def _make_applications(app_id: str, container: str, port: int, entity_name: str) -> dict:
    return {
        app_id: {
            "compose": {"services": {entity_name: {"name": container}}},
            "native_metrics": {"port": port},
        }
    }


class TestNativeMetricsTargetSuccess(unittest.TestCase):
    def test_returns_container_colon_port(self):
        apps = _make_applications("web-app-gitea", "gitea", 3000, "gitea")
        with patch("plugins.filter.native_metrics_target.get_entity_name", return_value="gitea"):
            result = native_metrics_target("web-app-gitea", apps)
        self.assertEqual(result, "gitea:3000")

    def test_different_app(self):
        apps = _make_applications("web-app-mattermost", "mattermost", 8067, "mattermost")
        with patch("plugins.filter.native_metrics_target.get_entity_name", return_value="mattermost"):
            result = native_metrics_target("web-app-mattermost", apps)
        self.assertEqual(result, "mattermost:8067")


class TestNativeMetricsTargetErrors(unittest.TestCase):
    def test_raises_when_container_name_missing(self):
        apps = {"web-app-gitea": {"compose": {"services": {}}, "native_metrics": {"port": 3000}}}
        with patch("plugins.filter.native_metrics_target.get_entity_name", return_value="gitea"):
            with self.assertRaises(AnsibleFilterError):
                native_metrics_target("web-app-gitea", apps)

    def test_raises_when_port_missing(self):
        apps = {"web-app-gitea": {"compose": {"services": {"gitea": {"name": "gitea"}}}, "native_metrics": {}}}
        with patch("plugins.filter.native_metrics_target.get_entity_name", return_value="gitea"):
            with self.assertRaises(AnsibleFilterError):
                native_metrics_target("web-app-gitea", apps)

    def test_raises_when_app_not_in_applications(self):
        with patch("plugins.filter.native_metrics_target.get_entity_name", return_value="gitea"):
            with self.assertRaises(AnsibleFilterError):
                native_metrics_target("web-app-gitea", {})


if __name__ == "__main__":
    unittest.main()
