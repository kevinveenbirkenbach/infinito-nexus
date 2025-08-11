import os
import glob
import re
import unittest


class RunOnceSchemaTest(unittest.TestCase):
    """
    Ensure that any occurrence of 'run_once_' in roles/*/tasks/main.yml
    matches the pattern 'run_once_' + (role_name with '-' replaced by '_'),
    unless the file explicitly deactivates its own run_once var via:
      # run_once_<role_suffix>: deactivated
    """

    RUN_ONCE_PATTERN = re.compile(r"run_once_([A-Za-z0-9_]+)")
    # Will be compiled per-file with the expected suffix:
    #   r"^\s*#\s*run_once_<suffix>\s*:\s*deactivated\s*$" (flags=MULTILINE|IGNORECASE)

    def test_run_once_suffix_matches_role(self):
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )
        violations = []

        pattern = os.path.join(project_root, 'roles', '*', 'tasks', 'main.yml')
        for filepath in glob.glob(pattern):
            parts = os.path.normpath(filepath).split(os.sep)
            try:
                role_index = parts.index('roles') + 1
                role_name = parts[role_index]
            except ValueError:
                continue

            expected_suffix = role_name.lower().replace('-', '_')

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Skip this file entirely if it explicitly deactivates its own run_once var
            deactivated_re = re.compile(
                rf"^\s*#\s*run_once_{re.escape(expected_suffix)}\s*:\s*deactivated\s*$",
                flags=re.IGNORECASE | re.MULTILINE,
            )
            if deactivated_re.search(content):
                continue

            matches = self.RUN_ONCE_PATTERN.findall(content)
            if not matches:
                continue

            for suffix in matches:
                if suffix != expected_suffix:
                    violations.append(
                        f"{filepath}: found run_once_{suffix}, expected run_once_{expected_suffix}"
                    )

        if violations:
            self.fail("Invalid run_once_ suffixes found:\n" + "\n".join(violations))


if __name__ == '__main__':
    unittest.main()
