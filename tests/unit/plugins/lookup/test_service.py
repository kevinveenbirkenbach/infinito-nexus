from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.service import LookupModule


_SERVICE_REGISTRY = {
    "matomo": {"role": "web-app-matomo"},
    "cdn": {"role": "web-svc-cdn"},
    "css": {"role": "web-svc-cdn", "canonical": "cdn"},
    "logout": {"role": "web-svc-logout"},
    "collab": {"role": "web-svc-collab"},
}


def _run(terms, applications, group_names, service_registry=None):
    kwargs = {}
    if service_registry is not None:
        kwargs["service_registry"] = service_registry
    return LookupModule().run(
        terms,
        variables={
            "applications": applications,
            "group_names": group_names,
        },
        **kwargs,
    )


class TestServiceDirect(unittest.TestCase):
    def setUp(self):
        self.applications = {
            "web-app-foo": {
                "compose": {
                    "services": {
                        "matomo": {"enabled": True, "shared": True},
                        "css": {"enabled": True, "shared": False},
                        "logout": {"enabled": False, "shared": True},
                    }
                }
            },
            "web-app-bar": {"compose": {"services": {}}},
        }

    def _get(self, term, group_names=None):
        return _run(
            [term],
            self.applications,
            group_names if group_names is not None else ["web-app-foo"],
            service_registry=_SERVICE_REGISTRY,
        )[0]

    def test_needed_true_when_enabled_and_shared(self):
        self.assertTrue(self._get("matomo")["needed"])

    def test_needed_false_when_enabled_only(self):
        self.assertFalse(self._get("cdn")["needed"])

    def test_needed_false_when_shared_only(self):
        self.assertFalse(self._get("logout")["needed"])

    def test_needed_false_when_service_absent(self):
        self.assertFalse(self._get("collab")["needed"])

    def test_needed_false_when_group_names_do_not_match(self):
        self.assertFalse(self._get("matomo", ["web-app-unknown"])["needed"])

    def test_needed_true_when_any_app_qualifies(self):
        self.assertTrue(self._get("matomo", ["web-app-bar", "web-app-foo"])["needed"])

    def test_enabled_shared_flags_are_aggregated_via_canonical_alias(self):
        result = self._get("cdn")
        self.assertTrue(result["enabled"])
        self.assertFalse(result["shared"])

    def test_lookup_by_role_name_uses_same_primary_service(self):
        by_key = self._get("cdn")
        by_role = self._get("web-svc-cdn")
        self.assertEqual(by_key, by_role)

    def test_multiple_terms(self):
        results = _run(
            ["matomo", "cdn", "logout"],
            self.applications,
            ["web-app-foo"],
            service_registry=_SERVICE_REGISTRY,
        )
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]["needed"])
        self.assertFalse(results[1]["needed"])
        self.assertFalse(results[2]["needed"])

    def test_empty_terms_returns_empty(self):
        self.assertEqual(
            _run(
                [],
                self.applications,
                ["web-app-foo"],
                service_registry=_SERVICE_REGISTRY,
            ),
            [],
        )


class TestServiceTransitive(unittest.TestCase):
    def setUp(self):
        self.applications = {
            "web-app-nextcloud": {
                "compose": {"services": {"collab": {"enabled": True}}}
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
        result = _run(
            ["matomo"],
            self.applications,
            ["web-app-nextcloud"],
            service_registry=_SERVICE_REGISTRY,
        )[0]
        self.assertTrue(result["needed"])

    def test_transitive_requires_shared_at_target(self):
        applications = {
            "web-app-nextcloud": {
                "compose": {"services": {"collab": {"enabled": True}}}
            },
            "web-svc-collab": {"compose": {"services": {"matomo": {"enabled": True}}}},
        }
        result = _run(
            ["matomo"],
            applications,
            ["web-app-nextcloud"],
            service_registry=_SERVICE_REGISTRY,
        )[0]
        self.assertFalse(result["needed"])

    def test_direct_provider_is_not_needed_without_shared_flag(self):
        result = _run(
            ["collab"],
            self.applications,
            ["web-app-nextcloud"],
            service_registry=_SERVICE_REGISTRY,
        )[0]
        self.assertFalse(result["needed"])


class TestServiceDiscoveryWithoutExplicitRegistry(unittest.TestCase):
    def test_role_local_provider_metadata_is_discovered_from_applications(self):
        applications = {
            "web-app-dashboard": {
                "compose": {
                    "services": {
                        "dashboard": {"enabled": False, "shared": True},
                    }
                }
            },
            "web-app-foo": {
                "compose": {
                    "services": {
                        "dashboard": {"enabled": True, "shared": True},
                    }
                }
            },
        }

        result = _run(["dashboard"], applications, ["web-app-foo"])[0]
        self.assertEqual(result["role"], "web-app-dashboard")
        self.assertTrue(result["needed"])

    def test_provides_and_canonical_are_discovered_from_provider_configs(self):
        applications = {
            "web-app-keycloak": {
                "compose": {
                    "services": {
                        "keycloak": {
                            "enabled": False,
                            "shared": True,
                            "provides": "oidc",
                        }
                    }
                }
            },
            "web-svc-cdn": {
                "compose": {
                    "services": {
                        "cdn": {"enabled": False, "shared": True},
                        "css": {"enabled": False, "shared": True, "canonical": "cdn"},
                    }
                }
            },
            "web-app-foo": {
                "compose": {
                    "services": {
                        "oidc": {"enabled": True, "shared": True},
                        "css": {"enabled": True, "shared": False},
                    }
                }
            },
        }

        oidc = _run(["oidc"], applications, ["web-app-foo"])[0]
        cdn = _run(["cdn"], applications, ["web-app-foo"])[0]

        self.assertEqual(oidc["role"], "web-app-keycloak")
        self.assertTrue(oidc["needed"])
        self.assertEqual(cdn["role"], "web-svc-cdn")
        self.assertTrue(cdn["enabled"])
        self.assertFalse(cdn["needed"])


class TestServiceCycleGuard(unittest.TestCase):
    def test_cycle_does_not_loop(self):
        applications = {
            "svc-a": {"compose": {"services": {"svc-b": {"enabled": True}}}},
            "svc-b": {"compose": {"services": {"svc-a": {"enabled": True}}}},
        }
        service_registry = {
            "svc-a": {"role": "svc-a"},
            "svc-b": {"role": "svc-b"},
            "logout": {"role": "web-svc-logout"},
        }
        result = _run(
            ["logout"],
            applications,
            ["svc-a"],
            service_registry=service_registry,
        )[0]
        self.assertFalse(result["needed"])

    def test_cycle_found_if_service_present(self):
        applications = {
            "svc-a": {
                "compose": {
                    "services": {
                        "svc-b": {"enabled": True},
                        "logout": {"enabled": True, "shared": True},
                    }
                }
            },
            "svc-b": {"compose": {"services": {"svc-a": {"enabled": True}}}},
        }
        service_registry = {
            "svc-a": {"role": "svc-a"},
            "svc-b": {"role": "svc-b"},
            "logout": {"role": "web-svc-logout"},
        }
        result = _run(
            ["logout"],
            applications,
            ["svc-b"],
            service_registry=service_registry,
        )[0]
        self.assertTrue(result["needed"])


class TestServiceErrors(unittest.TestCase):
    def test_raises_when_applications_missing(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(["matomo"], variables={"group_names": ["web-app-foo"]})

    def test_raises_when_applications_not_mapping(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={"applications": ["not", "a", "dict"], "group_names": []},
            )

    def test_raises_when_group_names_not_list(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={"applications": {}, "group_names": "not-a-list"},
            )

    def test_raises_when_service_registry_not_mapping(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run(
                ["matomo"],
                variables={"applications": {}, "group_names": []},
                service_registry="not-a-dict",
            )

    def test_raises_when_term_empty(self):
        with self.assertRaises(AnsibleError):
            _run(["   "], {}, [], service_registry=_SERVICE_REGISTRY)

    def test_raises_when_term_unknown(self):
        with self.assertRaises(AnsibleError):
            _run(["totally-unknown-key"], {}, [], service_registry=_SERVICE_REGISTRY)


if __name__ == "__main__":
    unittest.main()
