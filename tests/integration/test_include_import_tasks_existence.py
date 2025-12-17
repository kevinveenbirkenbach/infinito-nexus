import unittest
import os
import glob
import yaml
import re


class TestIncludeImportTasksExistence(unittest.TestCase):
    def setUp(self):
        # Determine project root, roles directory and list of YAML files to scan
        tests_dir = os.path.dirname(__file__)  # .../tests/integration
        project_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
        self.project_root = project_root
        self.roles_dir = os.path.join(project_root, "roles")

        self.files_to_scan = []
        for filepath in glob.glob(
            os.path.join(project_root, "**", "*.yml"), recursive=True
        ):
            # Skip .git and tests directories
            if "/.git/" in filepath or "/tests/" in filepath:
                continue
            self.files_to_scan.append(filepath)

    def _collect_task_includes(self, data):
        """
        Recursively collect all file references from include_tasks and import_tasks.
        Supports scalar syntax, block syntax ({ file: ... }), and block-list syntax.
        """
        task_files = []
        if isinstance(data, dict):
            for key, val in data.items():
                if key in ("include_tasks", "import_tasks"):
                    # Scalar syntax: include_tasks: tasks.yml
                    if isinstance(val, str):
                        task_files.append(val)
                    # Block syntax: include_tasks: { file: tasks.yml }
                    elif isinstance(val, dict) and "file" in val:
                        task_files.append(val["file"])
                    # Block-list syntax:
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "file" in item:
                                task_files.append(item["file"])
                else:
                    task_files.extend(self._collect_task_includes(val))
        elif isinstance(data, list):
            for item in data:
                task_files.extend(self._collect_task_includes(item))
        return task_files

    def test_include_import_tasks_exist(self):
        missing = []
        for file_path in self.files_to_scan:
            with open(file_path) as f:
                try:
                    documents = list(yaml.safe_load_all(f))
                except yaml.YAMLError:
                    self.fail(f"Failed to parse YAML in {file_path}")

            file_dir = os.path.dirname(file_path)
            # Determine the role context if under roles/
            role_name = None
            if self.roles_dir in file_dir:
                parts = file_dir.split(os.sep)
                idx = parts.index("roles")
                if idx + 1 < len(parts):
                    role_name = parts[idx + 1]
                    role_path_dir = os.path.join(self.roles_dir, role_name)

            for doc in documents:
                for task_ref in self._collect_task_includes(doc):
                    # Handle special Jinja2 vars
                    pattern_ref = task_ref
                    if "{{ role_path }}" in pattern_ref and role_name:
                        pattern_ref = pattern_ref.replace(
                            "{{ role_path }}", role_path_dir
                        )
                    if "{{ playbook_dir }}" in pattern_ref:
                        pattern_ref = pattern_ref.replace(
                            "{{ playbook_dir }}", self.project_root
                        )
                    # Replace other Jinja2 expressions with wildcard
                    pattern_ref = re.sub(r"\{\{.*?\}\}", "*", pattern_ref)
                    # If no extension, assume .yml
                    if not os.path.splitext(pattern_ref)[1]:
                        pattern_ref += ".yml"

                    # Prepare search globs
                    local_glob = os.path.join(file_dir, pattern_ref)
                    global_glob = os.path.join(self.project_root, pattern_ref)
                    tasks_dir_glob = os.path.join(
                        self.project_root, "tasks", pattern_ref
                    )
                    matches = []
                    matches += [p for p in glob.glob(local_glob) if os.path.isfile(p)]
                    matches += [p for p in glob.glob(global_glob) if os.path.isfile(p)]
                    matches += [
                        p for p in glob.glob(tasks_dir_glob) if os.path.isfile(p)
                    ]

                    if not matches:
                        missing.append((file_path, task_ref))

        if missing:
            messages = [
                f"File '{fp}' references missing task file '{tr}'" for fp, tr in missing
            ]
            self.fail("\n".join(messages))


if __name__ == "__main__":
    unittest.main()
