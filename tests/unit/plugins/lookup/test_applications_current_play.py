from __future__ import annotations

import unittest

from plugins.lookup.applications_current_play import LookupModule

SERVICE_REGISTRY = {
    "matomo": {"role": "web-app-matomo", "type": "frontend"},
    "asset": {"role": "web-svc-asset", "type": "frontend"},
    "ldap": {"role": "svc-db-openldap", "type": "backend"},
    "database": {"role_template": "svc-db-{type}", "type": "backend"},
}

SAMPLE_APPS = {
    "web-svc-html": {},
    "web-svc-legal": {},
    "web-svc-file": {},
    "web-svc-asset": {},
    "web-app-dashboard": {},
    "web-app-matomo": {},
    "svc-db-openldap": {},
    "svc-db-mariadb": {},
}


def _run(group_names, applications=None, meta_deps_map=None, service_registry=None):
    lm = LookupModule()
    lm._load_service_registry = lambda project_root: (
        service_registry if service_registry is not None else SERVICE_REGISTRY
    )
    lm._meta_deps = lambda role, roles_dir: (meta_deps_map or {}).get(role, [])
    apps = applications if applications is not None else SAMPLE_APPS
    return lm.run([], variables={"applications": apps, "group_names": group_names})[0]


class TestApplicationsIfGroupAndAllDeps(unittest.TestCase):
    # ------------------------------------------------------------------
    # Basic group filtering
    # ------------------------------------------------------------------

    def test_direct_group_only(self):
        result = _run(["web-svc-html"])
        self.assertIn("web-svc-html", result)
        self.assertNotIn("web-svc-legal", result)

    def test_unknown_group_returns_empty(self):
        self.assertEqual(_run(["nonexistent"]), {})

    def test_empty_group_names_returns_empty(self):
        self.assertEqual(_run([]), {})

    # ------------------------------------------------------------------
    # Meta dependency traversal
    # ------------------------------------------------------------------

    def test_meta_dep_included(self):
        result = _run(
            ["web-svc-legal"], meta_deps_map={"web-svc-legal": ["web-svc-html"]}
        )
        self.assertIn("web-svc-legal", result)
        self.assertIn("web-svc-html", result)

    def test_meta_dep_not_in_applications_ignored(self):
        result = _run(
            ["web-svc-legal"], meta_deps_map={"web-svc-legal": ["some-unknown-role"]}
        )
        self.assertIn("web-svc-legal", result)
        self.assertNotIn("some-unknown-role", result)

    def test_recursive_meta_deps(self):
        result = _run(
            ["web-svc-legal"],
            meta_deps_map={
                "web-svc-legal": ["web-svc-asset"],
                "web-svc-asset": ["web-svc-file"],
            },
        )
        self.assertIn("web-svc-legal", result)
        self.assertIn("web-svc-asset", result)
        self.assertIn("web-svc-file", result)

    def test_cycle_in_meta_deps_does_not_hang(self):
        result = _run(
            ["web-svc-html"],
            meta_deps_map={
                "web-svc-html": ["web-svc-legal"],
                "web-svc-legal": ["web-svc-html"],
            },
        )
        self.assertIn("web-svc-html", result)
        self.assertIn("web-svc-legal", result)

    # ------------------------------------------------------------------
    # Compose service dependency traversal
    # ------------------------------------------------------------------

    def test_service_dep_enabled_and_shared(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"matomo": {"enabled": True, "shared": True}}}
        }
        result = _run(["web-svc-legal"], applications=apps)
        self.assertIn("web-svc-legal", result)
        self.assertIn("web-app-matomo", result)

    def test_service_dep_not_included_when_enabled_false(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"matomo": {"enabled": False, "shared": True}}}
        }
        self.assertNotIn("web-app-matomo", _run(["web-svc-legal"], applications=apps))

    def test_service_dep_not_included_when_shared_false(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"matomo": {"enabled": True, "shared": False}}}
        }
        self.assertNotIn("web-app-matomo", _run(["web-svc-legal"], applications=apps))

    def test_service_not_in_registry_ignored(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"unknown-svc": {"enabled": True, "shared": True}}}
        }
        result = _run(["web-svc-legal"], applications=apps)
        self.assertIn("web-svc-legal", result)

    def test_service_role_template_resolved(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {
                "services": {
                    "database": {"enabled": True, "shared": True, "type": "mariadb"}
                }
            }
        }
        self.assertIn("svc-db-mariadb", _run(["web-svc-legal"], applications=apps))

    def test_service_role_template_without_type_ignored(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"database": {"enabled": True, "shared": True}}}
        }
        result = _run(["web-svc-legal"], applications=apps)
        self.assertFalse(any(k.startswith("svc-db-") for k in result))

    # ------------------------------------------------------------------
    # Mixed meta + service recursion
    # ------------------------------------------------------------------

    def test_mixed_meta_and_service_deps(self):
        apps = dict(SAMPLE_APPS)
        apps["web-svc-legal"] = {
            "compose": {"services": {"matomo": {"enabled": True, "shared": True}}}
        }
        result = _run(
            ["web-svc-legal"],
            applications=apps,
            meta_deps_map={"web-svc-legal": ["web-svc-html"]},
        )
        self.assertIn("web-svc-legal", result)
        self.assertIn("web-svc-html", result)
        self.assertIn("web-app-matomo", result)

    def test_transitive_service_dep(self):
        # web-svc-legal -meta-> web-svc-asset -service(ldap)-> svc-db-openldap
        apps = dict(SAMPLE_APPS)
        apps["web-svc-asset"] = {
            "compose": {"services": {"ldap": {"enabled": True, "shared": True}}}
        }
        result = _run(
            ["web-svc-legal"],
            applications=apps,
            meta_deps_map={"web-svc-legal": ["web-svc-asset"]},
        )
        self.assertIn("web-svc-legal", result)
        self.assertIn("web-svc-asset", result)
        self.assertIn("svc-db-openldap", result)

    # ------------------------------------------------------------------
    # Return value completeness
    # ------------------------------------------------------------------

    def test_returns_full_config_not_just_ids(self):
        apps = {
            "web-svc-legal": {"some_key": "some_value"},
            "web-svc-html": {"other_key": 42},
        }
        result = _run(
            ["web-svc-legal"],
            applications=apps,
            meta_deps_map={"web-svc-legal": ["web-svc-html"]},
        )
        self.assertEqual(result["web-svc-legal"], {"some_key": "some_value"})
        self.assertEqual(result["web-svc-html"], {"other_key": 42})

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def test_missing_applications_raises(self):
        lm = LookupModule()
        lm._load_service_registry = lambda p: {}
        lm._meta_deps = lambda r, d: []
        with self.assertRaises(Exception):
            lm.run([], variables={"group_names": []})

    def test_invalid_group_names_raises(self):
        lm = LookupModule()
        lm._load_service_registry = lambda p: {}
        lm._meta_deps = lambda r, d: []
        with self.assertRaises(Exception):
            lm.run(
                [], variables={"applications": SAMPLE_APPS, "group_names": "not-a-list"}
            )


if __name__ == "__main__":
    unittest.main()
