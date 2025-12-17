import unittest
import os
import yaml
from glob import glob
import re


class TestTopLevelVariableUsage(unittest.TestCase):
    def setUp(self):
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../")
        )
        # Braces werden von glob nicht unterstützt – also einzeln sammeln:
        self.roles_vars_paths = glob(
            os.path.join(self.project_root, "roles/*/vars/main.yml")
        ) + glob(os.path.join(self.project_root, "roles/*/defaults/main.yml"))
        self.group_vars_paths = glob(
            os.path.join(self.project_root, "group_vars/all/*.yml")
        )
        self.all_variable_files = self.roles_vars_paths + self.group_vars_paths
        self.valid_extensions = {
            ".yml",
            ".yaml",
            ".j2",
            ".py",
            ".sh",
            ".conf",
            ".env",
            ".xml",
            ".html",
            ".txt",
        }

    def get_top_level_keys(self, file_path):
        with open(file_path, "r") as f:
            try:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return list(data.keys())
            except yaml.YAMLError:
                pass
        return []

    def find_declaration_line(self, file_path, varname):
        """
        Findet die Zeilennummer (1-basiert), in der der Top-Level-Key wirklich deklariert wird.
        """
        pattern = re.compile(rf"^\s*{re.escape(varname)}\s*:")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if pattern.match(line) and not line.lstrip().startswith("#"):
                    return i
        return None

    def find_usage_in_project(self, varname, definition_path):
        """
        Sucht im gesamten Projekt nach varname, überspringt dabei
        nur die eine Deklarationszeile in definition_path.
        """
        decl_line = self.find_declaration_line(definition_path, varname)

        for root, _, files in os.walk(self.project_root):
            for fn in files:
                path = os.path.join(root, fn)
                ext = os.path.splitext(path)[1]
                if ext not in self.valid_extensions:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if (
                                path == definition_path
                                and decl_line is not None
                                and i == decl_line
                            ):
                                # genau die Deklarationszeile überspringen
                                continue
                            if varname in line:
                                return True
                except Exception:
                    continue
        return False

    def test_top_level_variable_usage(self):
        """
        Stellt sicher, dass jede Top-Level-Variable in roles/*/{vars,defaults}/main.yml
        und group_vars/all/*.yml irgendwo im Projekt (außer in ihrer eigenen
        Deklarationszeile) verwendet wird.
        """
        unused = []
        for varfile in self.all_variable_files:
            keys = self.get_top_level_keys(varfile)
            for key in keys:
                if not self.find_usage_in_project(key, varfile):
                    unused.append((varfile, key))

        if unused:
            msg = "\n".join(
                f"{path}: unused top-level key '{key}'" for path, key in unused
            )
            self.fail(
                "The following top-level variables are defined but never used:\n" + msg
            )


if __name__ == "__main__":
    unittest.main()
