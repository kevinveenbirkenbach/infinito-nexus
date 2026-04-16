from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.active_alertmanager_channels import LookupModule


def _make_applications(webhook_url: str = "") -> dict:
    """Build a minimal applications dict for web-app-prometheus.

    Candidates are derived from RECEIVER_CONFIG in the plugin itself —
    no communication_channels key needed in config.
    """
    return {
        "web-app-prometheus": {
            "alerting": {
                "mattermost": {"webhook_url": webhook_url},
            }
        }
    }


def _run(applications: dict, group_names: list) -> list:
    return LookupModule().run(
        [],
        variables={"applications": applications, "group_names": group_names},
    )[0]


class TestActiveAlertmanagerChannelsDeploymentCheck(unittest.TestCase):
    """group_names gate — app must be deployed on this host."""

    def test_includes_mailu_when_deployed(self):
        result = _run(_make_applications(), ["web-app-mailu"])
        self.assertIn("web-app-mailu", result)

    def test_excludes_mailu_when_not_deployed(self):
        result = _run(_make_applications(), [])
        self.assertNotIn("web-app-mailu", result)

    def test_excludes_mattermost_when_not_deployed(self):
        apps = _make_applications(webhook_url="https://mattermost.example/hook/abc")
        result = _run(apps, [])
        self.assertNotIn("web-app-mattermost", result)


class TestActiveAlertmanagerChannelsReceiverCheck(unittest.TestCase):
    """Receiver config gate — value must be non-empty."""

    def test_includes_mattermost_when_webhook_configured(self):
        apps = _make_applications(webhook_url="https://mattermost.example/hook/abc")
        result = _run(apps, ["web-app-mattermost"])
        self.assertIn("web-app-mattermost", result)

    def test_excludes_mattermost_when_webhook_empty(self):
        result = _run(_make_applications(webhook_url=""), ["web-app-mattermost"])
        self.assertNotIn("web-app-mattermost", result)

    def test_excludes_mattermost_when_webhook_whitespace_only(self):
        result = _run(_make_applications(webhook_url="   "), ["web-app-mattermost"])
        self.assertNotIn("web-app-mattermost", result)


class TestActiveAlertmanagerChannelsNotInRegistry(unittest.TestCase):
    """Apps absent from RECEIVER_CONFIG are excluded regardless of deployment."""

    def test_excludes_matrix_when_deployed(self):
        result = _run(_make_applications(), ["web-app-matrix"])
        self.assertNotIn("web-app-matrix", result)

    def test_excludes_matrix_even_with_all_groups(self):
        result = _run(
            _make_applications(),
            ["web-app-mailu", "web-app-mattermost", "web-app-matrix"],
        )
        self.assertNotIn("web-app-matrix", result)


class TestActiveAlertmanagerChannelsEmptyInputs(unittest.TestCase):
    """Edge cases: missing config and empty group_names."""

    def test_returns_empty_when_group_names_empty(self):
        result = _run(_make_applications(), [])
        self.assertEqual(result, [])

    def test_excludes_mattermost_when_prometheus_missing_from_applications(self):
        # webhook lookup returns "" when prometheus is absent — mattermost excluded.
        result = _run({}, ["web-app-mattermost"])
        self.assertNotIn("web-app-mattermost", result)


class TestActiveAlertmanagerChannelsErrors(unittest.TestCase):
    """Invalid inputs must raise AnsibleError."""

    def test_raises_when_applications_missing(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([], variables={})

    def test_raises_when_applications_not_a_dict(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([], variables={"applications": ["not", "a", "dict"]})


if __name__ == "__main__":
    unittest.main()
