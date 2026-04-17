from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.active_alertmanager_channels import LookupModule


def _make_applications(*app_ids: str, channels: tuple = ()) -> dict:
    """Build a minimal applications dict.

    apps listed in *channels* get communication.channel: true; others do not.
    """
    return {
        app_id: ({"communication": {"channel": True}} if app_id in channels else {})
        for app_id in app_ids
    }


def _run(applications: dict, group_names: list) -> list:
    return LookupModule().run(
        [],
        variables={"applications": applications, "group_names": group_names},
    )[0]


def _run_explicit(applications: dict, group_names: list) -> list:
    """Invoke with applications passed as explicit positional term — the template usage pattern."""
    return LookupModule().run(
        [applications],
        variables={"group_names": group_names},
    )[0]


class TestActiveAlertmanagerChannelsDeploymentCheck(unittest.TestCase):
    """group_names gate — app must be deployed on this host."""

    def test_includes_channel_when_deployed(self):
        apps = _make_applications(
            "web-app-mattermost", channels=("web-app-mattermost",)
        )
        result = _run(apps, ["web-app-mattermost"])
        self.assertIn("web-app-mattermost", result)

    def test_excludes_channel_when_not_deployed(self):
        apps = _make_applications(
            "web-app-mattermost", channels=("web-app-mattermost",)
        )
        result = _run(apps, [])
        self.assertNotIn("web-app-mattermost", result)

    def test_excludes_channel_when_deployed_but_not_in_group_names(self):
        apps = _make_applications(
            "web-app-mailu",
            "web-app-matrix",
            channels=("web-app-mailu", "web-app-matrix"),
        )
        result = _run(apps, ["web-app-mailu"])
        self.assertIn("web-app-mailu", result)
        self.assertNotIn("web-app-matrix", result)


class TestActiveAlertmanagerChannelsSelfDeclaration(unittest.TestCase):
    """communication.channel flag gate — must be true in app config."""

    def test_excludes_app_without_channel_flag(self):
        apps = _make_applications("web-app-mattermost")  # no channel flag
        result = _run(apps, ["web-app-mattermost"])
        self.assertNotIn("web-app-mattermost", result)

    def test_includes_all_declared_channels_when_deployed(self):
        apps = _make_applications(
            "web-app-mattermost",
            "web-app-matrix",
            "web-app-mailu",
            channels=("web-app-mattermost", "web-app-matrix", "web-app-mailu"),
        )
        result = _run(apps, ["web-app-mattermost", "web-app-matrix", "web-app-mailu"])
        self.assertCountEqual(
            result, ["web-app-mattermost", "web-app-matrix", "web-app-mailu"]
        )

    def test_result_is_sorted(self):
        apps = _make_applications(
            "web-app-mattermost",
            "web-app-matrix",
            "web-app-mailu",
            channels=("web-app-mattermost", "web-app-matrix", "web-app-mailu"),
        )
        result = _run(apps, ["web-app-mattermost", "web-app-matrix", "web-app-mailu"])
        self.assertEqual(result, sorted(result))

    def test_non_channel_apps_are_excluded(self):
        apps = _make_applications(
            "web-app-gitea",
            "web-app-nextcloud",
            "web-app-mattermost",
            channels=("web-app-mattermost",),
        )
        result = _run(
            apps, ["web-app-gitea", "web-app-nextcloud", "web-app-mattermost"]
        )
        self.assertNotIn("web-app-gitea", result)
        self.assertNotIn("web-app-nextcloud", result)
        self.assertIn("web-app-mattermost", result)


class TestActiveAlertmanagerChannelsEmptyInputs(unittest.TestCase):
    """Edge cases: empty applications and empty group_names."""

    def test_returns_empty_when_group_names_empty(self):
        apps = _make_applications(
            "web-app-mattermost", channels=("web-app-mattermost",)
        )
        result = _run(apps, [])
        self.assertEqual(result, [])

    def test_returns_empty_when_applications_empty(self):
        result = _run({}, ["web-app-mattermost"])
        self.assertEqual(result, [])

    def test_returns_empty_when_no_channels_declared(self):
        apps = _make_applications("web-app-gitea", "web-app-nextcloud")
        result = _run(apps, ["web-app-gitea", "web-app-nextcloud"])
        self.assertEqual(result, [])


class TestActiveAlertmanagerChannelsExplicitTerm(unittest.TestCase):
    """applications passed as explicit first term — matches template invocation pattern.

    Templates call lookup('active_alertmanager_channels', applications) to bypass the
    Ansible scoping issue where available_variables may contain the pre-merge inventory
    dict rather than the set_fact-merged result.
    """

    def test_includes_channel_when_deployed_explicit(self):
        apps = _make_applications("web-app-mattermost", channels=("web-app-mattermost",))
        result = _run_explicit(apps, ["web-app-mattermost"])
        self.assertIn("web-app-mattermost", result)

    def test_excludes_channel_when_not_deployed_explicit(self):
        apps = _make_applications("web-app-mattermost", channels=("web-app-mattermost",))
        result = _run_explicit(apps, [])
        self.assertEqual(result, [])

    def test_multiple_channels_explicit(self):
        apps = _make_applications(
            "web-app-mattermost", "web-app-matrix",
            channels=("web-app-mattermost", "web-app-matrix"),
        )
        result = _run_explicit(apps, ["web-app-mattermost", "web-app-matrix"])
        self.assertCountEqual(result, ["web-app-mattermost", "web-app-matrix"])


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
