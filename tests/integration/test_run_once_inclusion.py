import os
import re
import unittest
import glob
import yaml


def find_role_task_yml_files(root_dir):
    """
    Find all .yml or .yaml files under roles/*/tasks directories from project root.
    """
    pattern_yml = os.path.join(root_dir, "roles", "*", "tasks", "*.yml")
    pattern_yaml = os.path.join(root_dir, "roles", "*", "tasks", "*.yaml")
    return glob.glob(pattern_yml) + glob.glob(pattern_yaml)


class RunOnceInclusionTest(unittest.TestCase):
    """
    Ensure that every Ansible block in roles/*/tasks with a when condition matching
    either the dynamic Jinja scheme or a literal run_once_<role_name> is not defined,
    and containing an include_role/import_role also ends with
    include_tasks:  as its last task.
    """

    WHEN_PATTERN = re.compile(
        r"(?:run_once_\+\s*\(role_name\s*\|\s*lower\s*\|\s*replace\('\-','\_'\)\)\s*is\s*(?:not\s+)?defined"
        r"|run_once_[a-z0-9_]+\s*is\s*(?:not\s+)?defined)",
        re.IGNORECASE,
    )

    def test_run_once_blocks(self):
        # tests/integration -> tests -> project root
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        violations = []

        for filepath in find_role_task_yml_files(project_root):
            with open(filepath, "r") as f:
                try:
                    docs = list(yaml.safe_load_all(f))
                except yaml.YAMLError as e:
                    self.fail(f"Failed to parse YAML file {filepath}: {e}")

            for doc in docs:
                # Determine tasks list
                tasks = None
                if isinstance(doc, dict) and isinstance(doc.get("tasks"), list):
                    tasks = doc["tasks"]
                elif isinstance(doc, list):
                    tasks = doc
                if not tasks:
                    continue

                for item in tasks:
                    if not isinstance(item, dict) or "block" not in item:
                        continue
                    when = item.get("when")
                    if not isinstance(when, str) or not self.WHEN_PATTERN.search(when):
                        continue

                    block = item["block"]
                    # Check for include_role or import_role within block
                    has_role_include = any(
                        isinstance(t, dict)
                        and ("include_role" in t or "import_role" in t)
                        for t in block
                    )
                    # Check that last task is include_tasks:
                    last_task = block[-1] if block else None

                    has_run_once_flag = (
                        isinstance(last_task, dict)
                        and last_task.get("include_tasks") == "utils/once/flag.yml"
                    )

                    if has_role_include and not has_run_once_flag:
                        violations.append(
                            f"{filepath}: block with when='{when}' missing final include_tasks: utils/once/flag.yml"
                        )

        if violations:
            self.fail(
                "Run-once blocks missing include_tasks:\n" + "\n".join(violations)
            )


if __name__ == "__main__":
    unittest.main()
