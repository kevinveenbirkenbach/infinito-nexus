# tests/unit/lookup_plugins/test_tls_resolve.py

from __future__ import annotations

import unittest
from pathlib import Path
import sys

from ansible.errors import AnsibleError


# Ensure repo root is importable when running tests directly
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lookup_plugins.tls_resolve import LookupModule  # noqa: E402


class TestTlsResolve(unittest.TestCase):
    def _base_vars(self) -> dict:
        return {
            "domains": {
                # allow dict/list/str variants
                "web-app-bigbluebutton": {"canonical": "meet.infinito.example"},
                "web-app-nextcloud": [
                    "cloud.infinito.example",
                    "nextcloud.infinito.example",
                ],
                "web-app-keycloak": "auth.infinito.example",
            },
            "applications": {
                "web-app-bigbluebutton": {},
                "web-app-nextcloud": {},
                "web-app-keycloak": {},
            },
            "TLS_ENABLED": True,
            "TLS_MODE": "letsencrypt",
            "LETSENCRYPT_BASE_PATH": "/etc/letsencrypt",
            "LETSENCRYPT_LIVE_PATH": "/etc/letsencrypt/live",
            # only required when TLS resolves to self_signed
            "tls_selfsigned_base": "/srv/tls/selfsigned",
        }

    def _lookup(self, term: str, *, variables: dict | None = None, **kwargs):
        lm = LookupModule()
        return lm.run([term], variables=variables or self._base_vars(), **kwargs)

    def test_resolve_by_domain_auto(self):
        out = self._lookup("meet.infinito.example")[0]
        self.assertEqual(out["application_id"], "web-app-bigbluebutton")
        self.assertEqual(out["domain"], "meet.infinito.example")
        self.assertTrue(out["enabled"])
        self.assertEqual(out["mode"], "letsencrypt")
        self.assertEqual(out["protocols"]["web"], "https")
        self.assertEqual(out["ports"]["web"], 443)
        self.assertEqual(out["url"]["base"], "https://meet.infinito.example/")
        self.assertEqual(
            out["files"]["cert"],
            "/etc/letsencrypt/live/meet.infinito.example/fullchain.pem",
        )
        self.assertEqual(
            out["files"]["key"],
            "/etc/letsencrypt/live/meet.infinito.example/privkey.pem",
        )

    def test_resolve_by_app_id_auto(self):
        out = self._lookup("web-app-bigbluebutton")[0]
        self.assertEqual(out["application_id"], "web-app-bigbluebutton")
        self.assertEqual(out["domain"], "meet.infinito.example")

    def test_force_mode_domain(self):
        out = self._lookup("web-app-bigbluebutton", mode="domain")[0]
        self.assertEqual(out["application_id"], "web-app-bigbluebutton")
        self.assertEqual(out["domain"], "meet.infinito.example")

    def test_force_mode_app(self):
        out = self._lookup("meet.infinito.example", mode="app")[0]
        self.assertEqual(out["application_id"], "meet.infinito.example")
        self.assertEqual(out["domain"], "meet.infinito.example")

    def test_want_returns_subvalue(self):
        got = self._lookup("meet.infinito.example", want="files.cert")[0]
        self.assertEqual(
            got, "/etc/letsencrypt/live/meet.infinito.example/fullchain.pem"
        )

        got2 = self._lookup("meet.infinito.example", want="protocols.web")[0]
        self.assertEqual(got2, "https")

        got3 = self._lookup("meet.infinito.example", want="url.base")[0]
        self.assertEqual(got3, "https://meet.infinito.example/")

    def test_want_missing_path_raises(self):
        with self.assertRaises(AnsibleError):
            self._lookup("meet.infinito.example", want="files.does_not_exist")

    def test_missing_required_var_raises(self):
        vars_ = self._base_vars()
        vars_.pop("domains")
        with self.assertRaises(AnsibleError):
            self._lookup("meet.infinito.example", variables=vars_)

    def test_invalid_tls_mode_raises(self):
        vars_ = self._base_vars()
        vars_["TLS_MODE"] = "invalid"
        with self.assertRaises(AnsibleError):
            self._lookup("meet.infinito.example", variables=vars_)

    def test_invalid_forced_mode_raises(self):
        with self.assertRaises(AnsibleError):
            self._lookup("meet.infinito.example", mode="nope")

    def test_domain_not_found_raises(self):
        with self.assertRaises(AnsibleError):
            self._lookup("unknown.infinito.example")

    def test_ambiguous_domain_raises(self):
        vars_ = self._base_vars()
        vars_["domains"]["web-app-something-else"] = ["meet.infinito.example"]
        vars_["applications"]["web-app-something-else"] = {}
        with self.assertRaises(AnsibleError):
            self._lookup("meet.infinito.example", variables=vars_)

    def test_primary_domain_from_list(self):
        out = self._lookup("web-app-nextcloud")[0]
        self.assertEqual(out["domain"], "cloud.infinito.example")

    def test_primary_domain_from_str(self):
        out = self._lookup("web-app-keycloak")[0]
        self.assertEqual(out["domain"], "auth.infinito.example")

    def test_collect_all_domains_preserves_primary_and_uniqs(self):
        out = self._lookup("web-app-nextcloud")[0]
        self.assertEqual(
            out["domains"]["all"],
            ["cloud.infinito.example", "nextcloud.infinito.example"],
        )

    def test_san_default_is_all_domains(self):
        out = self._lookup("web-app-nextcloud")[0]
        self.assertEqual(
            out["domains"]["san"],
            ["cloud.infinito.example", "nextcloud.infinito.example"],
        )

    def test_san_override_includes_primary_and_uniqs(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-nextcloud"] = {
            "server": {
                "tls": {
                    "domains_san": ["alt1.infinito.example", "cloud.infinito.example"]
                }
            }
        }
        out = self._lookup("web-app-nextcloud", variables=vars_)[0]
        # primary first, then override(s) uniq
        self.assertEqual(
            out["domains"]["san"], ["cloud.infinito.example", "alt1.infinito.example"]
        )

    def test_per_app_enabled_override_off_forces_mode_off(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-bigbluebutton"] = {
            "server": {"tls": {"enabled": False}}
        }
        out = self._lookup("web-app-bigbluebutton", variables=vars_)[0]
        self.assertFalse(out["enabled"])
        self.assertEqual(out["mode"], "off")
        self.assertEqual(out["protocols"]["web"], "http")
        self.assertEqual(out["protocols"]["websocket"], "ws")
        self.assertEqual(out["ports"]["web"], 80)
        self.assertEqual(out["url"]["base"], "http://meet.infinito.example/")
        self.assertEqual(out["files"]["cert"], "")
        self.assertEqual(out["files"]["key"], "")

    def test_per_app_flavor_override_self_signed(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-bigbluebutton"] = {
            "server": {"tls": {"flavor": "self_signed"}}
        }
        out = self._lookup("web-app-bigbluebutton", variables=vars_)[0]
        self.assertTrue(out["enabled"])
        self.assertEqual(out["mode"], "self_signed")
        self.assertEqual(
            out["files"]["cert"],
            "/srv/tls/selfsigned/web-app-bigbluebutton/meet.infinito.example/fullchain.pem",
        )
        self.assertEqual(
            out["files"]["key"],
            "/srv/tls/selfsigned/web-app-bigbluebutton/meet.infinito.example/privkey.pem",
        )

    def test_self_signed_requires_tls_selfsigned_base(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-bigbluebutton"] = {
            "server": {"tls": {"flavor": "self_signed"}}
        }
        vars_.pop("tls_selfsigned_base", None)
        with self.assertRaises(AnsibleError):
            self._lookup("web-app-bigbluebutton", variables=vars_)

    def test_letsencrypt_name_override(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-bigbluebutton"] = {
            "server": {"tls": {"letsencrypt_cert_name": "bbb-cert"}}
        }
        out = self._lookup("web-app-bigbluebutton", variables=vars_)[0]
        self.assertEqual(
            out["files"]["cert"], "/etc/letsencrypt/live/bbb-cert/fullchain.pem"
        )
        self.assertEqual(
            out["files"]["key"], "/etc/letsencrypt/live/bbb-cert/privkey.pem"
        )

    def test_invalid_per_app_flavor_raises(self):
        vars_ = self._base_vars()
        vars_["applications"]["web-app-bigbluebutton"] = {
            "server": {"tls": {"flavor": "nope"}}
        }
        with self.assertRaises(AnsibleError):
            self._lookup("web-app-bigbluebutton", variables=vars_)

    def test_term_validation(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([], variables=self._base_vars())
        with self.assertRaises(AnsibleError):
            LookupModule().run(["a", "b"], variables=self._base_vars())
        with self.assertRaises(AnsibleError):
            self._lookup("   ")


if __name__ == "__main__":
    unittest.main()
