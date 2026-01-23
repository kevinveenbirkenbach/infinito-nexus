# tests/unit/lookup_plugins/test_cert_plan.py
import sys
import unittest
from ansible.errors import AnsibleError
from lookup_plugins.cert_plan import LookupModule

# Make "ansible.module_utils.tls_common" importable during plain unit tests.
import module_utils.tls_common as _tls_common

sys.modules.setdefault("ansible.module_utils.tls_common", _tls_common)


class TestCertPlanLookup(unittest.TestCase):
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
            "web-app-c": {
                "server": {
                    "tls": {"flavor": "self_signed", "domains_san": ["x.example"]}
                }
            },
            "web-app-off": {"server": {"tls": {"enabled": False}}},
        }

        self.vars = {
            "domains": self.domains,
            "applications": self.applications,
            "TLS_ENABLED": True,
            "TLS_MODE": "letsencrypt",
            "LETSENCRYPT_LIVE_PATH": "/etc/letsencrypt/live/",
            "TLS_SELFSIGNED_BASE_PATH": "/etc/infinito/selfsigned",
            "TLS_SELFSIGNED_SCOPE": "global",
        }

    def test_letsencrypt_plan_paths_and_sans_default(self):
        out = self.lookup.run(["web-app-a"], variables=self.vars, mode="app")[0]
        self.assertEqual(out["mode"], "letsencrypt")
        self.assertEqual(
            out["files"]["cert"], "/etc/letsencrypt/live/a.example/fullchain.pem"
        )
        self.assertEqual(
            out["files"]["key"], "/etc/letsencrypt/live/a.example/privkey.pem"
        )
        self.assertEqual(out["domains"]["san"], ["a.example"])

    def test_letsencrypt_plan_uses_cert_name_override(self):
        v = dict(self.vars)
        v["applications"] = dict(self.applications)
        v["applications"]["web-app-a"] = {
            "server": {"tls": {"letsencrypt_cert_name": "mycert"}}
        }

        out = self.lookup.run(["web-app-a"], variables=v, mode="app")[0]
        self.assertEqual(out["cert_id"], "mycert")
        self.assertEqual(
            out["files"]["cert"], "/etc/letsencrypt/live/mycert/fullchain.pem"
        )

    def test_selfsigned_global_scope(self):
        out = self.lookup.run(["web-app-b"], variables=self.vars, mode="app")[0]
        self.assertEqual(out["mode"], "self_signed")
        self.assertEqual(out["scope"], "global")
        self.assertEqual(out["cert_id"], "_global")
        self.assertEqual(
            out["files"]["cert"], "/etc/infinito/selfsigned/_global/fullchain.pem"
        )
        self.assertEqual(
            out["files"]["key"], "/etc/infinito/selfsigned/_global/privkey.pem"
        )

        # SANs: primary first, then rest of global list (deduped, normalized, first-seen)
        self.assertEqual(
            out["domains"]["san"],
            ["b.example", "a.example", "b-alt.example", "c.example", "api.c.example"],
        )

    def test_selfsigned_app_scope_paths(self):
        v = dict(self.vars)
        v["TLS_SELFSIGNED_SCOPE"] = "app"

        out = self.lookup.run(["web-app-b"], variables=v, mode="app")[0]
        self.assertEqual(out["scope"], "app")
        self.assertEqual(out["cert_id"], "web-app-b")
        self.assertEqual(
            out["files"]["cert"],
            "/etc/infinito/selfsigned/web-app-b/b.example/fullchain.pem",
        )
        self.assertEqual(
            out["files"]["key"],
            "/etc/infinito/selfsigned/web-app-b/b.example/privkey.pem",
        )

    def test_selfsigned_san_override(self):
        v = dict(self.vars)
        v["TLS_SELFSIGNED_SCOPE"] = "app"

        out = self.lookup.run(["web-app-c"], variables=v, mode="app")[0]
        self.assertEqual(out["domains"]["san"], ["c.example", "x.example"])

    def test_off_mode_returns_empty_files_and_san(self):
        v = dict(self.vars)
        v["domains"] = dict(self.domains)
        v["domains"]["web-app-off"] = "off.example"

        out = self.lookup.run(["web-app-off"], variables=v, mode="app")[0]
        self.assertEqual(out["enabled"], False)
        self.assertEqual(out["mode"], "off")
        self.assertEqual(out["files"]["cert"], "")
        self.assertEqual(out["files"]["key"], "")
        self.assertEqual(out["domains"]["san"], [])

    def test_want(self):
        val = self.lookup.run(
            ["web-app-a"], variables=self.vars, mode="app", want="files.cert"
        )[0]
        self.assertEqual(val, "/etc/letsencrypt/live/a.example/fullchain.pem")

    def test_missing_required_when_needed(self):
        v = dict(self.vars)
        del v["LETSENCRYPT_LIVE_PATH"]
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables=v, mode="app")

        v2 = dict(self.vars)
        v2["applications"] = dict(self.applications)
        v2["applications"]["web-app-a"] = {"server": {"tls": {"flavor": "self_signed"}}}
        del v2["TLS_SELFSIGNED_BASE_PATH"]
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables=v2, mode="app")

    def test_invalid_scope(self):
        v = dict(self.vars)
        v["TLS_SELFSIGNED_SCOPE"] = "nope"
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-b"], variables=v, mode="app")

    def test_invalid_tls_mode_default(self):
        v = dict(self.vars)
        v["TLS_MODE"] = "invalid"
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables=v, mode="app")


if __name__ == "__main__":
    unittest.main()
