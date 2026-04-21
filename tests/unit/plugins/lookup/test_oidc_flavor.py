import importlib
import importlib.util
import sys
import unittest
from pathlib import Path

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_module(rel_path: str, name: str):
    # Evict any stubbed utils.applications.config injected by sibling tests
    # (notably tests/unit/roles/web-app-keycloak/filter_plugins/test_redirect_uris.py,
    # whose setUpClass registers a stub `get()` with an incompatible signature
    # into sys.modules and never cleans up). Force the plugin to import the
    # real module from the repo.
    for key in (
        "utils.applications.config",
        "utils.applications",
        "utils",
    ):
        sys.modules.pop(key, None)
    importlib.import_module("utils.applications.config")

    path = _repo_root() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _apps(*, ldap_enabled=None, flavor=None, include_app=True):
    """Build a minimal `applications` dict for the Nextcloud role."""
    if not include_app:
        return {}
    oidc_block: dict = {}
    if flavor is not None:
        oidc_block["flavor"] = flavor
    services_block: dict = {"oidc": oidc_block}
    if ldap_enabled is not None:
        services_block["ldap"] = {"enabled": ldap_enabled}
    return {
        "web-app-nextcloud": {
            "compose": {
                "services": services_block,
            },
        },
    }


class OidcFlavorLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module(
            "plugins/lookup/oidc_flavor.py",
            "oidc_flavor",
        )

    def _run(self, applications, *, terms=None):
        lk = self.mod.LookupModule()
        return lk.run(terms or [], variables={"applications": applications})

    def test_ldap_enabled_returns_oidc_login(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=True)),
            ["oidc_login"],
        )

    def test_ldap_disabled_returns_sociallogin(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=False)),
            ["sociallogin"],
        )

    def test_ldap_missing_defaults_to_sociallogin(self):
        self.assertEqual(
            self._run(_apps()),
            ["sociallogin"],
        )

    def test_missing_application_defaults_to_sociallogin(self):
        self.assertEqual(
            self._run({"some-other-app": {}}),
            ["sociallogin"],
        )

    def test_explicit_flavor_overrides_ldap_fallback(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=True, flavor="sociallogin")),
            ["sociallogin"],
        )
        self.assertEqual(
            self._run(_apps(ldap_enabled=False, flavor="user_oidc")),
            ["user_oidc"],
        )

    def test_explicit_flavor_is_stripped(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=False, flavor="  oidc_login  ")),
            ["oidc_login"],
        )

    def test_blank_explicit_flavor_falls_back_to_ternary(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=True, flavor="   ")),
            ["oidc_login"],
        )
        self.assertEqual(
            self._run(_apps(ldap_enabled=False, flavor="")),
            ["sociallogin"],
        )

    def test_null_explicit_flavor_falls_back_to_ternary(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=True, flavor=None)),
            ["oidc_login"],
        )

    def test_non_string_explicit_flavor_is_ignored(self):
        self.assertEqual(
            self._run(_apps(ldap_enabled=True, flavor=42)),
            ["oidc_login"],
        )

    def test_rejects_positional_terms(self):
        lk = self.mod.LookupModule()
        with self.assertRaises(AnsibleError):
            lk.run(["unexpected"], variables={"applications": _apps()})

    def test_missing_applications_variable_raises(self):
        lk = self.mod.LookupModule()
        with self.assertRaises(AnsibleError):
            lk.run([], variables={})

    def test_applications_not_a_dict_raises(self):
        lk = self.mod.LookupModule()
        with self.assertRaises(AnsibleError):
            lk.run([], variables={"applications": ["not", "a", "dict"]})


if __name__ == "__main__":
    unittest.main()
