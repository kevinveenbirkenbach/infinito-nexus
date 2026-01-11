# tests/unit/lookup_plugins/test_docker_cards.py

import os
import sys
import tempfile
import shutil
import unittest

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

    def test_lookup_when_group_excludes_application_id(self):
        # Instantiate the LookupModule.
        lookup_module = LookupModule()
        # Set fake variables with group_names that do NOT include the application_id "portfolio".
        fake_variables = {
            "domains": {"portfolio": "myportfolio.com"},
            "applications": {
                "portfolio": {"docker": {"services": {"desktop": {"enabled": True}}}}
            },
            "group_names": [],  # Not including "portfolio"
        }
        result = lookup_module.run([self.test_roles_dir], variables=fake_variables)

        # Since the application_id is not in group_names, no card should be added.
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        cards = result[0]
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 0)


if __name__ == "__main__":
    unittest.main()
