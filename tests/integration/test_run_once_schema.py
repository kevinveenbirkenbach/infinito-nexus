import os
import glob
import re
import unittest
import yaml


class RunOnceSchemaTest(unittest.TestCase):
    """
    Ensure that any occurrence of 'run_once_' in roles/*/tasks/main.yml
    matches 'run_once_' + (role_name with '-' replaced by '_'),
    unless explicitly deactivated with:
      # run_once_<role_suffix>: deactivated
    Only block-level 'when' conditions in main.yml are considered.
    """

    def test_run_once_suffix_matches_role(self):
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        violations = []

        pattern = os.path.join(project_root, "roles", "*", "tasks", "main.yml")
        for filepath in glob.glob(pattern):
            role_name = os.path.normpath(filepath).split(os.sep)[-3]
            expected_suffix = role_name.lower().replace("-", "_")

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Skip this role if deactivated
            deactivated_re = re.compile(
                rf"^\s*#\s*run_once_{re.escape(expected_suffix)}\s*:\s*deactivated\s*$",
                flags=re.IGNORECASE | re.MULTILINE,
            )
            if deactivated_re.search(content):
                continue

            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                violations.append(f"{filepath}: YAML parse error: {e}")
                continue

            if not isinstance(data, list):
                continue

            for task in data:
                # Only check top-level blocks
                if isinstance(task, dict) and "block" in task:
                    when_clause = task.get("when")
                    if not when_clause:
                        continue
                    if isinstance(when_clause, list):
                        run_once_vars = [
                            w
                            for w in when_clause
                            if isinstance(w, str) and w.startswith("run_once_")
                        ]
                    elif isinstance(when_clause, str):
                        run_once_vars = (
                            [when_clause] if when_clause.startswith("run_once_") else []
                        )
                    else:
                        run_once_vars = []

                    for var in run_once_vars:
                        suffix = var[len("run_once_") :].split()[
                            0
                        ]  # strip any ' is not defined'
                        if suffix != expected_suffix:
                            violations.append(
                                f"{filepath}: found block-level {var}, expected run_once_{expected_suffix}"
                            )

        if violations:
            self.fail("Invalid run_once_ suffixes found:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
