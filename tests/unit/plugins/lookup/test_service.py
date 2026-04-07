from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.service import LookupModule

# Minimal service registry shared across tests.
_SERVICE_REGISTRY = {
    "matomo": {"role": "web-app-matomo", "type": "frontend"},
    "cdn": {"role": "web-svc-cdn", "type": "frontend"},
    "logout": {"role": "web-svc-logout", "type": "frontend"},
    "web-svc-collab": {"role": "web-svc-collab", "type": "frontend"},
    "database": {"role_template": "svc-db-{type}", "type": "backend"},
}


def _run(terms, applications, group_names, service_registry=None):
    return LookupModule().run(
        terms,
        variables={
            "applications": applications,
            "group_names": group_names,
            "SERVICE_REGISTRY": (
                service_registry if service_registry is not None else _SERVICE_REGISTRY
            ),
        },
    )


class TestServiceDirect(unittest.TestCase):
    """Direct (non-transitive) flag computation."""

    def setUp(self):
        self.applications = {
            "web-app-foo": {
                "compose": {
                    "services": {
                        "matomo": {"enabled": True, "shared": True},
                        "cdn": {"enabled": True, "shared": False},
                        "logout": {"enabled": False, "shared": True},
                    }
                }
            },
            "web-app-bar": {"compose": {"services": {}}},
        }

    def _get(self, term, group_names=None):
        gn = group_names if group_names is not None else ["web-app-foo"]
        return _run([term], self.applications, gn)[0]

    # --- needed (enabled AND shared) ---

    def test_needed_true_when_enabled_and_shared(self):
        r = self._get("matomo")
        self.assertTrue(r["needed"])

    def test_needed_false_when_enabled_only(self):
        r = self._get("cdn")
        self.assertFalse(r["needed"])

    def test_needed_false_when_shared_only(self):
        r = self._get("logout")
        self.assertFalse(r["needed"])

    def test_needed_false_when_service_absent(self):
        r = self._get("web-svc-collab")
        self.assertFalse(r["needed"])

    def test_needed_false_when_no_app_in_group_names(self):
        r = self._get("matomo", [])
        self.assertFalse(r["needed"])

    def test_needed_false_when_group_names_app_not_in_applications(self):
        r = self._get("matomo", ["web-app-unknown"])
        self.assertFalse(r["needed"])

    def test_needed_true_when_any_app_qualifies(self):
        r = self._get("matomo", ["web-app-bar", "web-app-foo"])
        self.assertTrue(r["needed"])

    # --- enabled flag ---

    def test_enabled_true_when_enabled(self):
        r = self._get("matomo")
        self.assertTrue(r["enabled"])

    def test_enabled_true_even_without_shared(self):
        r = self._get("cdn")
        self.assertTrue(r["enabled"])

    def test_enabled_false_when_only_shared(self):
        r = self._get("logout")
        self.assertFalse(r["enabled"])

    # --- shared flag ---

    def test_shared_true_when_shared(self):
        r = self._get("matomo")
        self.assertTrue(r["shared"])

    def test_shared_false_when_only_enabled(self):
        r = self._get("cdn")
        self.assertFalse(r["shared"])

    def test_shared_true_even_without_enabled(self):
        r = self._get("logout")
        self.assertTrue(r["shared"])

    # --- id / role fields ---

    def test_id_and_role_returned(self):
        r = self._get("matomo")
        self.assertEqual(r["id"], "matomo")
        self.assertEqual(r["role"], "web-app-matomo")

    # --- multiple terms ---

    def test_multiple_terms(self):
        results = _run(
            ["matomo", "cdn", "logout"],
            self.applications,
            ["web-app-foo"],
        )
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]["needed"])
        self.assertFalse(results[1]["needed"])
        self.assertFalse(results[2]["needed"])

    def test_empty_terms_returns_empty(self):
        results = _run([], self.applications, ["web-app-foo"])
        self.assertEqual(results, [])


class TestServiceBidirectionalMapping(unittest.TestCase):
    """Terms can be service keys or role names; both resolve to the same entry."""

    def setUp(self):
        self.applications = {
            "web-app-a": {
                "compose": {
                    "services": {
                        "matomo": {"enabled": True, "shared": True},
                    }
                }
            }
        }

    def test_lookup_by_key(self):
        r = _run(["matomo"], self.applications, ["web-app-a"])[0]
        self.assertEqual(r["id"], "matomo")
        self.assertEqual(r["role"], "web-app-matomo")
        self.assertTrue(r["needed"])

    def test_lookup_by_role(self):
        r = _run(["web-app-matomo"], self.applications, ["web-app-a"])[0]
        self.assertEqual(r["id"], "matomo")
        self.assertEqual(r["role"], "web-app-matomo")
        self.assertTrue(r["needed"])

    def test_key_and_role_produce_identical_result(self):
        by_key = _run(["matomo"], self.applications, ["web-app-a"])[0]
        by_role = _run(["web-app-matomo"], self.applications, ["web-app-a"])[0]
        self.assertEqual(by_key, by_role)

    def test_role_template_entry_resolved_by_key(self):
        # 'database' has role_template, no 'role' — resolved by key
        r = _run(["database"], self.applications, ["web-app-a"])[0]
        self.assertEqual(r["id"], "database")
        self.assertEqual(r["role"], "svc-db-{type}")


class TestServiceTransitive(unittest.TestCase):
    """Transitive resolution via enabled service dependencies.

    Transitive resolution follows SERVICE_REGISTRY so short service keys recurse
    via their provider role ids instead of requiring full application ids.
    """

    def setUp(self):
        # web-app-nextcloud declares web-svc-collab (full app ID) as enabled
        # web-svc-collab itself has matomo enabled+shared
        # => nextcloud transitively needs matomo
        self.applications = {
            "web-app-nextcloud": {
                "compose": {
                    "services": {
                        "web-svc-collab": {"enabled": True},
                    }
                }
            },
            "web-svc-collab": {
                "compose": {
                    "services": {
                        "matomo": {"enabled": True, "shared": True},
                    }
                }
            },
        }

    def test_transitive_needed_resolved(self):
        r = _run(["matomo"], self.applications, ["web-app-nextcloud"])[0]
        self.assertTrue(r["needed"])

    def test_direct_provider_needed(self):
        r = _run(["web-svc-collab"], self.applications, ["web-app-nextcloud"])[0]
        # web-app-nextcloud has web-svc-collab enabled but NOT shared, so needed=False
        self.assertFalse(r["needed"])

    def test_false_for_unknown_in_apps(self):
        r = _run(["logout"], self.applications, ["web-app-nextcloud"])[0]
        self.assertFalse(r["needed"])

    def test_short_key_resolves_transitively_via_registry_role(self):
        service_registry = dict(_SERVICE_REGISTRY)
        service_registry["collab"] = {"role": "web-svc-collab", "type": "frontend"}
        applications = {
            "web-app-nextcloud": {
                "compose": {"services": {"collab": {"enabled": True}}}
            },
            "web-svc-collab": {
                "compose": {"services": {"matomo": {"enabled": True, "shared": True}}}
            },
        }
        r = _run(
            ["matomo"],
            applications,
            ["web-app-nextcloud"],
            service_registry=service_registry,
        )[0]
        self.assertTrue(r["needed"])

    def test_role_template_resolves_transitively_via_service_type(self):
        applications = {
            "web-app-nextcloud": {
                "compose": {
                    "services": {
                        "database": {"enabled": True, "type": "mariadb"},
                    }
                }
            },
            "svc-db-mariadb": {
                "compose": {
                    "services": {
                        "logout": {"enabled": True, "shared": True},
                    }
                }
            },
        }
        r = _run(["logout"], applications, ["web-app-nextcloud"])[0]
        self.assertTrue(r["needed"])

    def test_transitive_requires_shared_at_target(self):
        # If matomo is enabled but not shared at web-svc-collab, needed stays False
        applications = {
            "web-app-nextcloud": {
                "compose": {"services": {"web-svc-collab": {"enabled": True}}}
            },
            "web-svc-collab": {
                "compose": {"services": {"matomo": {"enabled": True}}}  # no shared
            },
        }
        r = _run(["matomo"], applications, ["web-app-nextcloud"])[0]
        self.assertFalse(r["needed"])


class TestServiceCycleGuard(unittest.TestCase):
    """Circular service dependencies must not cause infinite recursion."""

    def setUp(self):
        self.applications = {
            "svc-a": {"compose": {"services": {"svc-b": {"enabled": True}}}},
            "svc-b": {"compose": {"services": {"svc-a": {"enabled": True}}}},
        }
        self.service_registry = {
            "svc-a": {"role": "svc-a", "type": "backend"},
            "svc-b": {"role": "svc-b", "type": "backend"},
            "logout": {"role": "web-svc-logout", "type": "frontend"},
        }

    def test_cycle_does_not_loop(self):
        r = _run(
            ["logout"],
            self.applications,
            ["svc-a"],
            service_registry=self.service_registry,
        )[0]
        self.assertFalse(r["needed"])

    def test_cycle_found_if_service_present(self):
        self.applications["svc-a"]["compose"]["services"]["logout"] = {
            "enabled": True,
            "shared": True,
        }
        r = _run(
            ["logout"],
            self.applications,
            ["svc-b"],
            service_registry=self.service_registry,
        )[0]
        self.assertTrue(r["needed"])


class TestServiceErrors(unittest.TestCase):
    def test_raises_when_applications_missing(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={
                    "group_names": ["web-app-foo"],
                    "SERVICE_REGISTRY": _SERVICE_REGISTRY,
                },
            )

    def test_raises_when_applications_not_mapping(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={
                    "applications": ["not", "a", "dict"],
                    "group_names": [],
                    "SERVICE_REGISTRY": _SERVICE_REGISTRY,
                },
            )

    def test_raises_when_group_names_not_list(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={
                    "applications": {},
                    "group_names": "not-a-list",
                    "SERVICE_REGISTRY": _SERVICE_REGISTRY,
                },
            )

    def test_raises_when_service_registry_missing(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={"applications": {}, "group_names": []},
            )

    def test_raises_when_service_registry_not_mapping(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={
                    "applications": {},
                    "group_names": [],
                    "SERVICE_REGISTRY": "not-a-dict",
                },
            )

    def test_raises_when_term_empty(self):
        with self.assertRaises(AnsibleError):
            _run(["   "], {}, [])

    def test_raises_when_term_unknown(self):
        with self.assertRaises(AnsibleError):
            _run(["totally-unknown-key"], {}, [])


if __name__ == "__main__":
    unittest.main()
