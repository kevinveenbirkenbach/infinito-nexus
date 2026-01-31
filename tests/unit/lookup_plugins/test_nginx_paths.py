# tests/unit/lookup_plugins/test_nginx_paths.py
import unittest
from unittest.mock import patch

from ansible.errors import AnsibleError

# Adjust if your repo uses a different import root
from lookup_plugins.nginx_paths import LookupModule


class _FakeTlsResolveLookup:
    """
    Minimal fake lookup plugin compatible with both call styles:
      - run([domain], variables=..., want="protocols.web")
      - run([domain], variables=...)
    """

    def __init__(self, protocol: str):
        self._protocol = protocol

    def run(self, terms, variables=None, **kwargs):
        want = kwargs.get("want", "")
        if want and want != "protocols.web":
            raise AssertionError(f"Unexpected want passed to tls_resolve: {want}")
        return [self._protocol]


class TestNginxPathsLookup(unittest.TestCase):
    def setUp(self):
        self.plugin = LookupModule()
        self.variables = {
            "applications": {"svc-prx-openresty": {"docker": {"volumes": {}}}},
        }

    def _fake_get_app_conf(self, applications, app_id, key, strict=True):
        if key == "docker.volumes.www":
            return "/opt/mock/www"
        if key == "docker.volumes.nginx":
            return "/opt/mock/nginx"
        raise KeyError(key)

    def test_base_structure(self):
        with patch(
            "lookup_plugins.nginx_paths.get_app_conf",
            side_effect=self._fake_get_app_conf,
        ):
            out = self.plugin.run([], variables=self.variables)[0]

        self.assertIn("files", out)
        self.assertIn("directories", out)
        self.assertIn("user", out)

        self.assertEqual(out["files"]["configuration"], "/opt/mock/nginx/nginx.conf")

        conf = out["directories"]["configuration"]
        self.assertEqual(conf["base"], "/opt/mock/nginx/conf.d/")
        self.assertEqual(conf["global"], "/opt/mock/nginx/conf.d/global/")
        self.assertEqual(conf["servers"], "/opt/mock/nginx/conf.d/servers/")
        self.assertEqual(conf["maps"], "/opt/mock/nginx/conf.d/maps/")
        self.assertEqual(conf["streams"], "/opt/mock/nginx/conf.d/streams/")

        self.assertEqual(
            conf["http_includes"],
            [
                "/opt/mock/nginx/conf.d/global/",
                "/opt/mock/nginx/conf.d/maps/",
                "/opt/mock/nginx/conf.d/servers/http/",
                "/opt/mock/nginx/conf.d/servers/https/",
            ],
        )

        data = out["directories"]["data"]
        self.assertEqual(data["www"], "/opt/mock/www/")
        self.assertEqual(data["html"], "/opt/mock/www/public_html/")
        self.assertEqual(data["files"], "/opt/mock/www/public_files/")
        self.assertEqual(data["cdn"], "/opt/mock/www/public_cdn/")
        self.assertEqual(data["global"], "/opt/mock/www/global/")
        self.assertEqual(data["well_known"], "/usr/share/nginx/well-known/")

        cache = out["directories"]["cache"]
        self.assertEqual(cache["general"], "/tmp/cache_nginx_general/")
        self.assertEqual(cache["image"], "/tmp/cache_nginx_image/")

        ensure = out["directories"]["ensure"]
        ensure_paths = out["directories"]["ensure_paths"]

        self.assertIsInstance(ensure, list)
        self.assertIsInstance(ensure_paths, list)
        self.assertEqual(ensure_paths, [d["path"] for d in ensure])

        self.assertIn({"path": "/tmp/cache_nginx_general/", "mode": "0700"}, ensure)
        self.assertIn({"path": "/tmp/cache_nginx_image/", "mode": "0700"}, ensure)

        # well_known is container path → must NOT be part of host dir creation
        self.assertNotIn("/usr/share/nginx/well-known/", ensure_paths)

    def test_domain_uses_tls_resolve_when_no_override(self):
        fake_tls = _FakeTlsResolveLookup("https")

        with (
            patch(
                "lookup_plugins.nginx_paths.get_app_conf",
                side_effect=self._fake_get_app_conf,
            ),
            patch(
                "lookup_plugins.nginx_paths.lookup_loader.get",
                return_value=fake_tls,
            ),
        ):
            out = self.plugin.run(["example.com"], variables=self.variables)[0]

        self.assertEqual(out["domain"]["name"], "example.com")
        self.assertEqual(out["domain"]["protocol"], "https")
        self.assertFalse(out["domain"]["protocol_overridden"])
        self.assertEqual(
            out["files"]["domain"],
            "/opt/mock/nginx/conf.d/servers/https/example.com.conf",
        )

    def test_domain_protocol_override_http(self):
        # tls_resolve should NOT be consulted when override is present
        with (
            patch(
                "lookup_plugins.nginx_paths.get_app_conf",
                side_effect=self._fake_get_app_conf,
            ),
            patch(
                "lookup_plugins.nginx_paths.lookup_loader.get",
                side_effect=AssertionError(
                    "tls_resolve must not be called when protocol override is set"
                ),
            ),
        ):
            out = self.plugin.run(
                ["example.com"], variables=self.variables, protocol="http"
            )[0]

        self.assertEqual(out["domain"]["protocol"], "http")
        self.assertTrue(out["domain"]["protocol_overridden"])
        self.assertEqual(
            out["files"]["domain"],
            "/opt/mock/nginx/conf.d/servers/http/example.com.conf",
        )

    def test_invalid_protocol_override_raises(self):
        with patch(
            "lookup_plugins.nginx_paths.get_app_conf",
            side_effect=self._fake_get_app_conf,
        ):
            with self.assertRaises(AnsibleError):
                self.plugin.run(
                    ["example.com"], variables=self.variables, protocol="ftp"
                )

    def test_too_many_terms_raises(self):
        with patch(
            "lookup_plugins.nginx_paths.get_app_conf",
            side_effect=self._fake_get_app_conf,
        ):
            with self.assertRaises(AnsibleError):
                self.plugin.run(["a.example", "b.example"], variables=self.variables)

    def test_want_projection(self):
        with patch(
            "lookup_plugins.nginx_paths.get_app_conf",
            side_effect=self._fake_get_app_conf,
        ):
            out = self.plugin.run(
                [], variables=self.variables, want="directories.configuration.base"
            )

        self.assertEqual(out, ["/opt/mock/nginx/conf.d/"])


if __name__ == "__main__":
    unittest.main()
