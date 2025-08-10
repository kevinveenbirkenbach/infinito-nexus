# tests/unit/roles/web-app-keycloak/filter_plugins/test_redirect_uris.py
import os
import sys
import types
import unittest
import importlib.util

PLUGIN_REL_PATH = os.path.join("roles", "web-app-keycloak", "filter_plugins", "redirect_uris.py")


def _find_repo_root_containing(rel_path, max_depth=8):
    """Walk upwards from this test file to find the repo root that contains rel_path."""
    here = os.path.dirname(__file__)
    cur = here
    for _ in range(max_depth):
        candidate = os.path.join(cur, rel_path)
        if os.path.isfile(candidate):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise FileNotFoundError(f"Could not find {rel_path} upwards from {here}")


def _load_module_from_path(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Cannot load spec for {file_path}"
    spec.loader.exec_module(module)
    return module


class RedirectUrisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create stub package: module_utils, with config_utils and get_url submodules.
        mu = types.ModuleType("module_utils")
        mu_config = types.ModuleType("module_utils.config_utils")
        mu_geturl = types.ModuleType("module_utils.get_url")

        # Define stub exceptions
        class AppConfigKeyError(Exception):
            pass

        class ConfigEntryNotSetError(Exception):
            pass

        # Define a practical get_app_conf that understands dotted keys
        def get_app_conf(applications, app_id, dotted, default=None):
            data = applications.get(app_id, {})
            cur = data
            for part in dotted.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return cur

        # Define a simple get_url matching your module_utils/get_url contract
        # get_url(domains, application_id, protocol) -> "<protocol>://<domain>"
        def get_url(domains, application_id, protocol):
            domain = domains[application_id]
            return f"{protocol}://{domain}"

        # Attach to stub modules
        mu_config.get_app_conf = staticmethod(get_app_conf)
        mu_config.AppConfigKeyError = AppConfigKeyError
        mu_config.ConfigEntryNotSetError = ConfigEntryNotSetError

        mu_geturl.get_url = staticmethod(get_url)

        # Register in sys.modules so plugin imports succeed
        sys.modules["module_utils"] = mu
        sys.modules["module_utils.config_utils"] = mu_config
        sys.modules["module_utils.get_url"] = mu_geturl

        # Load the plugin by path
        repo_root = _find_repo_root_containing(PLUGIN_REL_PATH)
        plugin_path = os.path.join(repo_root, PLUGIN_REL_PATH)
        cls.plugin = _load_module_from_path("test_target.redirect_uris", plugin_path)

        # Keep originals for per-test monkeypatching
        cls._orig_get_app_conf = cls.plugin.get_app_conf
        cls._orig_get_url = cls.plugin.get_url

    def tearDown(self):
        # Restore plugin functions if a test monkeypatched them
        self.plugin.get_app_conf = self._orig_get_app_conf
        self.plugin.get_url = self._orig_get_url

    def test_single_domain_oauth2_enabled(self):
        domains = {"app1": "example.org"}
        applications = {"app1": {"features": {"oauth2": True}}}
        result = self.plugin.redirect_uris(domains, applications, web_protocol="https")
        self.assertEqual(result, ["https://example.org/*"])

    def test_multiple_domains_oidc_enabled(self):
        domains = {"appX": ["a.example.org", "b.example.org"]}
        applications = {"appX": {"features": {"oidc": True}}}
        result = self.plugin.redirect_uris(domains, applications, web_protocol="https")
        self.assertCountEqual(result, ["https://a.example.org/*", "https://b.example.org/*"])

    def test_feature_missing_is_skipped(self):
        domains = {"app1": "example.org"}
        applications = {"app1": {"features": {"oauth2": False, "oidc": False}}}
        result = self.plugin.redirect_uris(domains, applications)
        self.assertEqual(result, [])

    def test_protocol_and_wildcard_customization(self):
        domains = {"app1": "x.test"}
        applications = {"app1": {"features": {"oauth2": True}}}
        result = self.plugin.redirect_uris(domains, applications, web_protocol="http", wildcard="/cb")
        self.assertEqual(result, ["http://x.test/cb"])

    def test_dedup_default_true(self):
        domains = {"app1": ["dup.test", "dup.test", "other.test"]}
        applications = {"app1": {"features": {"oidc": True}}}
        result = self.plugin.redirect_uris(domains, applications)
        self.assertEqual(result, ["https://dup.test/*", "https://other.test/*"])

    def test_dedup_false_keeps_duplicates(self):
        domains = {"app1": ["dup.test", "dup.test"]}
        applications = {"app1": {"features": {"oidc": True}}}
        result = self.plugin.redirect_uris(domains, applications, dedup=False)
        self.assertEqual(result, ["https://dup.test/*", "https://dup.test/*"])

    def test_invalid_domains_type_raises(self):
        with self.assertRaises(self.plugin.AnsibleFilterError):
            self.plugin.redirect_uris(["not-a-dict"], {})  # type: ignore[arg-type]

    def test_get_url_failure_is_wrapped(self):
        # Make get_url raise an arbitrary error; plugin should re-raise AnsibleFilterError
        def boom(*args, **kwargs):
            raise RuntimeError("boom")
        self.plugin.get_url = boom

        domains = {"app1": "example.org"}
        applications = {"app1": {"features": {"oauth2": True}}}

        with self.assertRaises(self.plugin.AnsibleFilterError) as ctx:
            self.plugin.redirect_uris(domains, applications)
        self.assertIn("get_url failed", str(ctx.exception))

    def test_get_app_conf_exception_is_handled_as_no_feature(self):
        # Make get_app_conf raise AppConfigKeyError; plugin should treat as not enabled and skip
        def raising_get_app_conf(*args, **kwargs):
            raise self.plugin.AppConfigKeyError("missing key")
        self.plugin.get_app_conf = raising_get_app_conf

        domains = {"app1": "example.org"}
        applications = {"app1": {"features": {"oauth2": True}}}  # value won't be read due to exception

        result = self.plugin.redirect_uris(domains, applications)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
