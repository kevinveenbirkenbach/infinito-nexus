# tests/unit/lookup_plugins/test_tls_resolve.py
import sys
import unittest
from ansible.errors import AnsibleError
from lookup_plugins.tls_resolve import LookupModule

# Make "ansible.module_utils.tls_common" importable during plain unit tests.
import module_utils.tls_common as _tls_common

sys.modules.setdefault("ansible.module_utils.tls_common", _tls_common)


class TestTlsResolveLookup(unittest.TestCase):
    def setUp(self):
        self.lookup = LookupModule()

        self.domains = {
            "web-app-a": "a.example",
            "web-app-b": ["b.example", "b-alt.example"],
            "web-app-c": {"primary": "c.example", "api": "api.c.example"},
        }

        self.applications = {
            "web-app-a": {},
            "web-app-b": {"server": {"tls": {"flavor": "self_signed"}}},
            "web-app-c": {"server": {"tls": {"enabled": False}}},
        }

        self.base_vars = {
            "domains": self.domains,
            "applications": self.applications,
            "TLS_ENABLED": True,
            "TLS_MODE": "letsencrypt",
        }

    def test_domain_term_auto_mode(self):
        out = self.lookup.run(["a.example"], variables=self.base_vars)[0]
        self.assertEqual(out["application_id"], "web-app-a")
        self.assertEqual(out["domain"], "a.example")
        self.assertTrue(out["enabled"])
        self.assertEqual(out["mode"], "letsencrypt")
        self.assertEqual(out["protocols"]["web"], "https")
        self.assertEqual(out["ports"]["web"], 443)
        self.assertEqual(out["url"]["base"], "https://a.example/")

    def test_app_term_forced_app(self):
        out = self.lookup.run(["web-app-a"], variables=self.base_vars, mode="app")[0]
        self.assertEqual(out["application_id"], "web-app-a")
        self.assertEqual(out["domain"], "a.example")

    def test_app_override_flavor(self):
        out = self.lookup.run(["web-app-b"], variables=self.base_vars, mode="app")[0]
        self.assertEqual(out["mode"], "self_signed")

    def test_app_override_enabled_false(self):
        out = self.lookup.run(["web-app-c"], variables=self.base_vars, mode="app")[0]
        self.assertFalse(out["enabled"])
        self.assertEqual(out["mode"], "off")
        self.assertEqual(out["protocols"]["web"], "http")
        self.assertEqual(out["ports"]["web"], 80)

    def test_domains_all_contains_primary_first(self):
        out = self.lookup.run(["web-app-b"], variables=self.base_vars, mode="app")[0]
        self.assertEqual(out["domains"]["primary"], "b.example")
        self.assertEqual(out["domains"]["all"], ["b.example", "b-alt.example"])

    def test_want_path_returns_scalar(self):
        val = self.lookup.run(
            ["web-app-a", "url.base"], variables=self.base_vars, mode="app"
        )[0]
        self.assertEqual(val, "https://a.example/")

    def test_missing_required_vars(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables={})

    def test_invalid_tls_mode_default(self):
        bad = dict(self.base_vars)
        bad["TLS_MODE"] = "invalid"
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables=bad, mode="app")

    def test_invalid_forced_mode(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables=self.base_vars, mode="nope")


if __name__ == "__main__":
    unittest.main()
