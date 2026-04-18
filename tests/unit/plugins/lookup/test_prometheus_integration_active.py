from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.prometheus_integration_active import LookupModule


def _make_applications(
    *app_ids: str,
    prometheus_deps: tuple = (),
) -> dict:
    """Build a minimal applications dict.

    Apps listed in *prometheus_deps* get compose.services.prometheus.enabled: true.
    """
    apps = {}
    for app_id in app_ids:
        if app_id in prometheus_deps:
            apps[app_id] = {"compose": {"services": {"prometheus": {"enabled": True}}}}
        else:
            apps[app_id] = {}
    return apps


def _run(applications: dict, application_id: str, group_names: list) -> bool:
    return LookupModule().run(
        [],
        variables={
            "applications": applications,
            "application_id": application_id,
            "group_names": group_names,
        },
    )[0]


def _run_explicit(applications: dict, application_id: str, group_names: list) -> bool:
    """Invoke with applications and application_id as explicit positional terms — the template usage pattern."""
    return LookupModule().run(
        [applications, application_id],
        variables={
            "group_names": group_names,
        },
    )[0]


class TestPrometheusIntegrationActiveDeploymentCheck(unittest.TestCase):
    """group_names gate — web-app-prometheus must be on this host."""

    def test_false_when_prometheus_not_in_group_names(self):
        apps = _make_applications("web-app-gitea", prometheus_deps=("web-app-gitea",))
        result = _run(apps, "web-app-gitea", [])
        self.assertFalse(result)

    def test_false_when_prometheus_not_deployed_even_with_dep(self):
        apps = _make_applications("web-app-gitea", prometheus_deps=("web-app-gitea",))
        result = _run(apps, "web-app-gitea", ["web-app-gitea"])
        self.assertFalse(result)


class TestPrometheusIntegrationActivePrometheusVhost(unittest.TestCase):
    """When the current app IS web-app-prometheus the result is always True."""

    def test_true_for_prometheus_vhost_itself(self):
        apps = _make_applications("web-app-prometheus")
        result = _run(apps, "web-app-prometheus", ["web-app-prometheus"])
        self.assertTrue(result)

    def test_true_for_prometheus_vhost_even_without_service_dep(self):
        # web-app-prometheus doesn't need its own service dep — it IS the host.
        apps = {"web-app-prometheus": {}}
        result = _run(apps, "web-app-prometheus", ["web-app-prometheus"])
        self.assertTrue(result)


class TestPrometheusIntegrationActiveServiceDep(unittest.TestCase):
    """compose.services.prometheus.enabled gate for non-prometheus vhosts."""

    def test_true_when_app_declares_prometheus_dep(self):
        apps = _make_applications("web-app-gitea", prometheus_deps=("web-app-gitea",))
        result = _run(apps, "web-app-gitea", ["web-app-prometheus", "web-app-gitea"])
        self.assertTrue(result)

    def test_false_when_app_has_no_prometheus_dep(self):
        apps = _make_applications("web-app-gitea")
        result = _run(apps, "web-app-gitea", ["web-app-prometheus", "web-app-gitea"])
        self.assertFalse(result)

    def test_false_when_prometheus_dep_disabled(self):
        apps = {
            "web-app-gitea": {
                "compose": {"services": {"prometheus": {"enabled": False}}}
            }
        }
        result = _run(apps, "web-app-gitea", ["web-app-prometheus", "web-app-gitea"])
        self.assertFalse(result)


class TestPrometheusIntegrationActiveExplicitTerm(unittest.TestCase):
    """applications and application_id passed as explicit terms — matches template invocation pattern.

    Templates call lookup('prometheus_integration_active', applications, application_id) to bypass
    Ansible scoping issues where available_variables may contain stale values.
    """

    def test_true_when_app_declares_prometheus_dep_explicit(self):
        apps = _make_applications("web-app-gitea", prometheus_deps=("web-app-gitea",))
        result = _run_explicit(
            apps, "web-app-gitea", ["web-app-prometheus", "web-app-gitea"]
        )
        self.assertTrue(result)

    def test_false_when_app_has_no_prometheus_dep_explicit(self):
        apps = _make_applications("web-app-gitea")
        result = _run_explicit(
            apps, "web-app-gitea", ["web-app-prometheus", "web-app-gitea"]
        )
        self.assertFalse(result)

    def test_true_for_prometheus_vhost_explicit(self):
        apps = _make_applications("web-app-prometheus")
        result = _run_explicit(apps, "web-app-prometheus", ["web-app-prometheus"])
        self.assertTrue(result)


class TestPrometheusIntegrationActiveErrors(unittest.TestCase):
    """Invalid inputs must raise AnsibleError."""

    def test_raises_when_applications_missing(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([], variables={})

    def test_raises_when_applications_not_a_dict(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([], variables={"applications": ["not", "a", "dict"]})


if __name__ == "__main__":
    unittest.main()
