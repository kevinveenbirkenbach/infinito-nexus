import os
import sys
import tempfile
import shutil
import unittest
from ansible.errors import AnsibleError

# Adjust the PYTHONPATH to include the lookup_plugins folder from the web-app-desktop role.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "../../../roles/web-app-desktop/lookup_plugins"
    ),
)

from docker_cards import LookupModule


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

    def test_lookup_when_group_includes_application_id(self):
        # Instantiate the LookupModule.
        lookup_module = LookupModule()

        # Define dummy variables including group_names that contain the application_id "portfolio".
        fake_variables = {
            "domains": {"portfolio": "myportfolio.com"},
            "applications": {
                "portfolio": {"docker": {"services": {"desktop": {"enabled": True}}}}
            },
            "group_names": ["portfolio"],
            "WEB_PROTOCOL": "https",
        }

        result = lookup_module.run([self.test_roles_dir], variables=fake_variables)

        # The result is a list containing one list of card dictionaries.
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        # Since "portfolio" is in group_names, one card should be present.
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

        result = lookup_module.run([self.test_roles_dir], variables=fake_variables)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 1)

        card = cards[0]
        self.assertEqual(card["url"], "https://myportfolio.com")

    def test_lookup_url_uses_http_when_web_protocol_is_http(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()
        fake_variables["WEB_PROTOCOL"] = "http"

        result = lookup_module.run([self.test_roles_dir], variables=fake_variables)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 1)

        card = cards[0]
        self.assertEqual(card["url"], "http://myportfolio.com")

    def test_lookup_raises_error_when_web_protocol_is_missing(self):
        lookup_module = LookupModule()
        fake_variables = self._base_fake_variables()
        fake_variables.pop("WEB_PROTOCOL", None)

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

        result = lookup_module.run([self.test_roles_dir], variables=fake_variables)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 0)


if __name__ == "__main__":
    unittest.main()
