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

    Exception (per-when item):
      If the *same line* that contains the run_once_ condition also contains:
        # pass test_run_once_suffix_matches_role
      then this specific condition is ignored by this test.

    Only block-level 'when' conditions in main.yml are considered.
    """

    PASS_MARKER = "pass test_run_once_suffix_matches_role"

    @staticmethod
    def _run_once_vars_from_when(when_clause):
        if isinstance(when_clause, list):
            return [
                w
                for w in when_clause
                if isinstance(w, str) and w.startswith("run_once_")
            ]
        if isinstance(when_clause, str):
            return [when_clause] if when_clause.startswith("run_once_") else []
        return []

    @classmethod
    def _has_pass_marker_for_var(cls, content: str, var: str) -> bool:
        """
        Check whether the exact list-item line that contains `var` also contains the PASS_MARKER.
        Example line in YAML:
          - run_once_svc_db_openldap is not defined   # pass test_run_once_suffix_matches_role
        """
        line_re = re.compile(
            rf"^\s*-\s*{re.escape(var)}\s*(#.*\b{re.escape(cls.PASS_MARKER)}\b.*)?\s*$",
            flags=re.IGNORECASE | re.MULTILINE,
        )
        m = line_re.search(content)
        return bool(m and m.group(1))

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
                if not (isinstance(task, dict) and "block" in task):
                    continue

                when_clause = task.get("when")
                if not when_clause:
                    continue

                run_once_vars = self._run_once_vars_from_when(when_clause)
                if not run_once_vars:
                    continue

                for var in run_once_vars:
                    # Allow per-line opt-out with marker comment in the source YAML
                    if self._has_pass_marker_for_var(content, var):
                        continue

                    # strip any ' is not defined' etc.
                    suffix = var[len("run_once_") :].split()[0]
                    if suffix != expected_suffix:
                        violations.append(
                            f"{filepath}: found block-level {var}, expected run_once_{expected_suffix}"
                        )

        if violations:
            self.fail("Invalid run_once_ suffixes found:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
