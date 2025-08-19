import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch

# Absoluter Pfad zum tree.py Script (wie im vorhandenen Test)
SCRIPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../cli/build/tree.py")
)

class TestTreeIncludeRoleDependencies(unittest.TestCase):
    def setUp(self):
        # Temp roles root
        self.roles_dir = tempfile.mkdtemp()

        # Producer-Role (die wir scannen) + Zielrollen für Matches
        self.producer = "producer"
        self.producer_path = os.path.join(self.roles_dir, self.producer)
        os.makedirs(os.path.join(self.producer_path, "tasks"))
        os.makedirs(os.path.join(self.producer_path, "meta"))

        # Rollen, die durch Pattern/Loops gematcht werden sollen
        self.roles_to_create = [
            "sys-ctl-hlth-webserver",
            "sys-ctl-hlth-csp",
            "svc-db-postgres",
            "svc-db-mysql",
            "axb",          # für a{{database_type}}b → a*b
            "ayyb",         # für a{{database_type}}b → a*b
            "literal-role", # für reinen Literalnamen
        ]
        for r in self.roles_to_create:
            os.makedirs(os.path.join(self.roles_dir, r, "meta"), exist_ok=True)

        # tasks/main.yml mit allen geforderten Varianten
        tasks_yaml = """
- name: Include health dependencies
  include_role:
    name: "{{ item }}"
  loop:
    - sys-ctl-hlth-webserver
    - sys-ctl-hlth-csp

- name: Pattern with literal + var suffix
  include_role:
    name: "svc-db-{{database_type}}"

- name: Pattern with literal prefix/suffix around var
  include_role:
    name: "a{{database_type}}b"

- name: Pure variable only (should be ignored)
  include_role:
    name: "{{database_type}}"

- name: Pure literal include
  include_role:
    name: "literal-role"
"""
        with open(os.path.join(self.producer_path, "tasks", "main.yml"), "w", encoding="utf-8") as f:
            f.write(tasks_yaml)

        # shadow folder
        self.shadow_dir = tempfile.mkdtemp()

        # Patch argv
        self.orig_argv = sys.argv[:]
        sys.argv = [
            SCRIPT_PATH,
            "-d", self.roles_dir,
            "-s", self.shadow_dir,
            "-o", "json",
        ]

        # Ensure project root on sys.path
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../")
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

    def tearDown(self):
        sys.argv = self.orig_argv
        shutil.rmtree(self.roles_dir)
        shutil.rmtree(self.shadow_dir)

    @patch("cli.build.tree.output_graph")
    @patch("cli.build.tree.build_mappings")
    def test_include_role_dependencies_detected(self, mock_build_mappings, mock_output_graph):
        # Basis-Graph leer, damit nur unsere Dependencies sichtbar sind
        mock_build_mappings.return_value = {}

        # Import und Ausführen
        import importlib
        tree_mod = importlib.import_module("cli.build.tree")
        tree_mod.main()

        # Erwarteter Pfad im Shadow-Folder
        expected_tree_path = os.path.join(
            self.shadow_dir, self.producer, "meta", "tree.json"
        )
        self.assertTrue(
            os.path.isfile(expected_tree_path),
            f"tree.json not found at {expected_tree_path}"
        )

        # JSON laden und Abhängigkeiten prüfen
        with open(expected_tree_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Erwartete include_role-Dependenzen:
        expected = sorted([
            "sys-ctl-hlth-webserver", # aus loop
            "sys-ctl-hlth-csp",       # aus loop
            "svc-db-postgres",        # aus svc-db-{{database_type}}
            "svc-db-mysql",           # aus svc-db-{{database_type}}
            "axb",                    # aus a{{database_type}}b
            "ayyb",                   # aus a{{database_type}}b
            "literal-role",           # reiner Literalname
        ])

        deps = (
            data
            .get("dependencies", {})
            .get("include_role", [])
        )
        self.assertEqual(deps, expected, "include_role dependencies mismatch")

        # Sicherstellen, dass der pure Variable-Name "{{database_type}}" NICHT aufgenommen wurde
        self.assertNotIn("{{database_type}}", deps, "pure variable include should be ignored")

        # Sicherstellen, dass im Original-meta der Producer-Role nichts geschrieben wurde
        original_tree_path = os.path.join(self.producer_path, "meta", "tree.json")
        self.assertFalse(
            os.path.exists(original_tree_path),
            "tree.json should NOT be written to the real meta/ folder"
        )

if __name__ == "__main__":
    unittest.main()
