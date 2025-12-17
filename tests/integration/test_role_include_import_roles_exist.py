import unittest
import os
import glob
import yaml
import re


class TestIncludeImportRoleExistence(unittest.TestCase):
    def setUp(self):
        # Determine project root and roles directory
        tests_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
        self.roles_dir = os.path.join(project_root, "roles")
        # Collect all .yml files in project (recursive), excluding .git and tests dirs
        self.files_to_scan = []
        for filepath in glob.glob(
            os.path.join(project_root, "**", "*.yml"), recursive=True
        ):
            # Skip .git, tests folders
            if "/.git/" in filepath or "/tests/" in filepath:
                continue
            self.files_to_scan.append(filepath)

    def _collect_includes(self, data):
        """
        Recursively collect all roles referenced via include_role or import_role.
        Supports scalar, block, and block-list syntax, plus templating and wildcards.
        """
        roles = []
        if isinstance(data, dict):
            for key, val in data.items():
                if key in ("include_role", "import_role"):
                    # Scalar syntax: include_role: role_name
                    if isinstance(val, str):
                        roles.append(val)
                    # Block syntax: include_role: { name: role_name }
                    elif isinstance(val, dict) and "name" in val:
                        roles.append(val["name"])
                    # Block-list syntax: include_role:
                    #  - name: foo
                    #  - name: bar
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "name" in item:
                                roles.append(item["name"])
                else:
                    roles.extend(self._collect_includes(val))
        elif isinstance(data, list):
            for item in data:
                roles.extend(self._collect_includes(item))
        return roles

    def test_include_import_roles_exist(self):
        missing = []
        for file_path in self.files_to_scan:
            with open(file_path) as f:
                try:
                    docs = list(yaml.safe_load_all(f))
                except yaml.YAMLError:
                    self.fail(f"Failed to parse YAML in {file_path}")

            for doc in docs:
                # Skip empty YAML documents (e.g. only "---")
                if doc is None:
                    continue

                for role_name in self._collect_includes(doc):
                    # NEW: Validate that role_name is a proper string
                    if not isinstance(role_name, str) or not role_name.strip():
                        self.fail(
                            "Invalid include_role/import_role name detected.\n"
                            f"  • File: {file_path}\n"
                            f"  • Extracted name value: {repr(role_name)}\n"
                            "The 'name:' field must contain a non-empty string.\n"
                            "Example:\n"
                            "  include_role:\n"
                            "    name: my-role-name\n"
                        )

                    # Convert Jinja2 templates and wildcards to glob patterns
                    pattern = re.sub(r"\{\{.*?\}\}", "*", role_name)
                    glob_path = os.path.join(self.roles_dir, pattern)

                    matches = [p for p in glob.glob(glob_path) if os.path.isdir(p)]
                    if not matches:
                        missing.append((file_path, role_name))

        if missing:
            messages = [
                f"File '{fp}' references missing role '{rn}'" for fp, rn in missing
            ]
            self.fail("\n".join(messages))


if __name__ == "__main__":
    unittest.main()
