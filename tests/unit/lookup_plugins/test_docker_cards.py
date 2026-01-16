import os
import sys
import tempfile
import shutil
import unittest

from ansible.errors import AnsibleError
from jinja2 import Environment, StrictUndefined


# Adjust the PYTHONPATH to include the lookup_plugins folder from the web-app-desktop role.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "../../../roles/web-app-desktop/lookup_plugins"
    ),
)

from docker_cards import LookupModule


def _ansible_bool(value):
    """
    Minimal Ansible-like bool filter for unit tests.
    Mirrors common Ansible truthy/falsey handling for strings.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"y", "yes", "true", "on", "1"}:
            return True
        if v in {"n", "no", "false", "off", "0", ""}:
            return False
    return bool(value)


class DummyTemplar:
    """
    Small, deterministic templating stub for unit tests.
    It is intentionally minimal: only supports rendering Jinja strings
    and provides an Ansible-like `bool` filter.
    """

    def __init__(self, variables):
        self._vars = variables
        self._env = Environment(undefined=StrictUndefined)
        self._env.filters["bool"] = _ansible_bool

    def template(self, value):
        if value is None:
            return value

        # Keep non-strings untouched
        if not isinstance(value, str):
            return value

        # Only render if it looks like a Jinja template
        if "{{" in value and "}}" in value:
            tmpl = self._env.from_string(value)
            return tmpl.render(**self._vars)

        return value


class TestDockerCardsLookup(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to simulate the roles directory.
        self.test_roles_dir = tempfile.mkdtemp(prefix="test_roles_")

        # Create a sample role "web-app-desktop" under that directory.
        self.role_name = "web-app-desktop"
        self.role_dir = os.path.join(self.test_roles_dir, self.role_name)
        os.makedirs(os.path.join(self.role_dir, "meta"))
        os.makedirs(os.path.join(self.role_dir, "vars"))

        vars_main = os.path.join(self.role_dir, "vars", "main.yml")
        with open(vars_main, "w", encoding="utf-8") as f:
            f.write("application_id: portfolio\n")

        # Create a sample README.md with a H1 line for the title.
        readme_path = os.path.join(self.role_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Portfolio Application\nThis is a sample portfolio role.")

        # Create a sample meta/main.yml in the meta folder.
        meta_main_path = os.path.join(self.role_dir, "meta", "main.yml")
        meta_yaml = """
galaxy_info:
  description: "A role for deploying a portfolio application."
  logo:
    class: fa-solid fa-briefcase
"""
        with open(meta_main_path, "w", encoding="utf-8") as f:
            f.write(meta_yaml)

    def tearDown(self):
        # Remove the temporary roles directory after the test.
        shutil.rmtree(self.test_roles_dir)

    def _base_fake_variables(self):
        return {
            "domains": {"portfolio": "myportfolio.com"},
            "applications": {
                "portfolio": {"docker": {"services": {"desktop": {"enabled": True}}}}
            },
            "group_names": ["portfolio"],
        }

    def _run_lookup(self, lookup_module, fake_variables):
        # Provide deterministic templating behavior for unit tests.
        lookup_module._templar = DummyTemplar(fake_variables)
        return lookup_module.run([self.test_roles_dir], variables=fake_variables)

    def test_lookup_when_group_includes_application_id(self):
        lookup_module = LookupModule()

        fake_variables = {
            "domains": {"portfolio": "myportfolio.com"},
            "applications": {
                "portfolio": {"docker": {"services": {"desktop": {"enabled": True}}}}
            },
            "group_names": ["portfolio"],
            "WEB_PROTOCOL": "https",
        }

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 1)

        card = cards[0]
        self.assertEqual(card["title"], "Portfolio Application")
        self.assertEqual(card["text"], "A role for deploying a portfolio application.")
        self.assertEqual(card["icon"]["class"], "fa-solid fa-briefcase")
        self.assertEqual(card["url"], "https://myportfolio.com")
        self.assertTrue(card["iframe"])

    def test_lookup_url_uses_https_when_web_protocol_is_https(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()
        fake_variables["WEB_PROTOCOL"] = "https"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "https://myportfolio.com")

    def test_lookup_url_uses_http_when_web_protocol_is_http(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()
        fake_variables["WEB_PROTOCOL"] = "http"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "http://myportfolio.com")

    def test_lookup_raises_error_when_web_protocol_is_missing(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()
        fake_variables.pop("WEB_PROTOCOL", None)

        # Still set templar so the plugin behaves like runtime (even if it errors before templating).
        lookup_module._templar = DummyTemplar(fake_variables)

        with self.assertRaises(AnsibleError) as ctx:
            lookup_module.run([self.test_roles_dir], variables=fake_variables)

        self.assertIn("WEB_PROTOCOL", str(ctx.exception))

    def test_lookup_when_group_excludes_application_id(self):
        lookup_module = LookupModule()
        fake_variables = {
            "domains": {"portfolio": "myportfolio.com"},
            "applications": {
                "portfolio": {"docker": {"services": {"desktop": {"enabled": True}}}}
            },
            "group_names": [],  # Not including "portfolio"
            "WEB_PROTOCOL": "https",
        }

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 0)

    def test_lookup_url_renders_web_protocol_jinja_https(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()

        fake_variables["TLS_ENABLED"] = True
        fake_variables["WEB_PROTOCOL"] = "{{ 'https' if TLS_ENABLED | bool else 'http' }}"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "https://myportfolio.com")

    def test_lookup_url_renders_web_protocol_jinja_http(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()

        fake_variables["TLS_ENABLED"] = False
        fake_variables["WEB_PROTOCOL"] = "{{ 'https' if TLS_ENABLED | bool else 'http' }}"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "http://myportfolio.com")

    def test_lookup_url_renders_domain_url_jinja(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()

        fake_variables["domains"] = {"portfolio": "{{ DOMAIN_PRIMARY }}"}
        fake_variables["DOMAIN_PRIMARY"] = "myportfolio.com"
        fake_variables["WEB_PROTOCOL"] = "https"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "https://myportfolio.com")

    def test_lookup_url_renders_web_protocol_jinja_when_tls_enabled_is_string(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()

        fake_variables["TLS_ENABLED"] = "true"
        fake_variables["WEB_PROTOCOL"] = "{{ 'https' if TLS_ENABLED | bool else 'http' }}"

        result = self._run_lookup(lookup_module, fake_variables)

        self.assertEqual(result[0][0]["url"], "https://myportfolio.com")


if __name__ == "__main__":
    unittest.main()
