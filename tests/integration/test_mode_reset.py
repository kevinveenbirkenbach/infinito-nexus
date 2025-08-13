#!/usr/bin/env python3
import os
import re
import unittest

# Base directory for roles (adjust if needed)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../roles'))

class TestModeResetIntegration(unittest.TestCase):
    """
    Verify that a role either mentioning 'MODE_RESET' under tasks/ OR containing a reset file:
      - provides a *_reset.yml (or reset.yml) in tasks/,
      - includes it exactly once across tasks/*.yml,
      - and the include is guarded in the SAME task block by a non-commented `when`
        that contains `MODE_RESET | bool` (inline, list, or array).
    Additional conditions (e.g., `and something`) are allowed.
    Commented-out conditions (e.g., `#when: ...` or `# include_tasks: ...`) do NOT count.
    """

    def test_mode_reset_tasks(self):
        for role_name in os.listdir(BASE_DIR):
            with self.subTest(role=role_name):
                role_path = os.path.join(BASE_DIR, role_name)
                tasks_dir = os.path.join(role_path, 'tasks')

                if not os.path.isdir(tasks_dir):
                    self.skipTest(f"Role '{role_name}' has no tasks directory.")

                # Gather all task files
                task_files = []
                for root, _, files in os.walk(tasks_dir):
                    for fname in files:
                        if fname.lower().endswith(('.yml', '.yaml')):
                            task_files.append(os.path.join(root, fname))

                # Detect any 'MODE_RESET' usage
                mode_reset_found = False
                for fp in task_files:
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            if 'MODE_RESET' in f.read():
                                mode_reset_found = True
                                break
                    except (UnicodeDecodeError, OSError):
                        continue

                # Detect reset files in tasks/ root
                try:
                    task_root_listing = os.listdir(tasks_dir)
                except OSError:
                    task_root_listing = []
                reset_files = [
                    fname for fname in task_root_listing
                    if fname.endswith('_reset.yml') or fname == 'reset.yml'
                ]

                # Decide if this role must be validated:
                # - if it mentions MODE_RESET anywhere under tasks/, OR
                # - if it has a reset file in tasks/ root
                should_check = mode_reset_found or bool(reset_files)
                if not should_check:
                    self.skipTest(f"Role '{role_name}': no MODE_RESET usage and no reset file found.")

                # If we check, a reset file MUST exist
                self.assertTrue(
                    reset_files,
                    f"Role '{role_name}': expected a *_reset.yml or reset.yml in tasks/."
                )

                # Patterns to find non-commented reset include occurrences
                def include_patterns(rf: str):
                    # Accept:
                    #   - include_tasks: reset.yml (quoted or unquoted)
                    #   - ansible.builtin.include_tasks: reset.yml
                    #   - include_tasks:\n  file: reset.yml
                    # All must be non-commented (no leading '#')
                    q = r'(?:' + re.escape(rf) + r'|"' + re.escape(rf) + r'"|\'' + re.escape(rf) + r'\')'
                    return [
                        re.compile(
                            rf'(?m)^(?<!#)\s*-?\s*(?:ansible\.builtin\.)?include_tasks:\s*{q}\s*$'
                        ),
                        re.compile(
                            rf'(?ms)^(?<!#)\s*-?\s*(?:ansible\.builtin\.)?include_tasks:\s*\n[^-\S\r\n]*file:\s*{q}\s*$'
                        ),
                    ]

                include_occurrences = []  # (file_path, reset_file, (span_start, span_end))

                # Search every tasks/*.yml for exactly one include of any reset file
                for fp in task_files:
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            content = f.read()
                        for rf in reset_files:
                            for patt in include_patterns(rf):
                                for m in patt.finditer(content):
                                    include_occurrences.append((fp, rf, m.span()))
                    except (UnicodeDecodeError, OSError):
                        continue

                self.assertGreater(
                    len(include_occurrences), 0,
                    f"Role '{role_name}': must include one of {reset_files} in some non-commented tasks/*.yml."
                )
                self.assertEqual(
                    len(include_occurrences), 1,
                    f"Role '{role_name}': reset include must appear exactly once across tasks/*.yml, "
                    f"found {len(include_occurrences)}."
                )

                # Verify a proper 'when' containing 'MODE_RESET | bool' exists in the SAME task block
                include_fp, included_rf, span = include_occurrences[0]

                with open(include_fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.splitlines()

                # Compute the line index where the include occurs
                include_line_idx = content.count('\n', 0, span[0])

                def is_task_start(line: str) -> bool:
                    # new task begins with "- " at current indentation
                    return re.match(r'^\s*-\s', line) is not None

                # Expand upwards to task start
                start_idx = include_line_idx
                while start_idx > 0 and not is_task_start(lines[start_idx]):
                    start_idx -= 1
                # Expand downwards to next task start or EOF
                end_idx = include_line_idx
                while end_idx + 1 < len(lines) and not is_task_start(lines[end_idx + 1]):
                    end_idx += 1

                task_block = "\n".join(lines[start_idx:end_idx + 1])

                # Build regexes that:
                #  - DO NOT match commented lines (require ^\s*when: not preceded by '#')
                #  - Allow additional conditions inline (and/or/parentheses/etc.)
                #  - Support list form and yaml array form
                when_inline = re.search(
                    r'(?m)^(?<!#)\s*when:\s*(?!\[)(?:(?!\n).)*MODE_RESET\s*\|\s*bool',
                    task_block
                )
                when_list = re.search(
                    r'(?ms)^(?<!#)\s*when:\s*\n'                # non-commented when:
                    r'(?:(?:\s*#.*\n)|(?:\s*-\s*.*\n))*'         # comments or other list items
                    r'\s*-\s*[^#\n]*MODE_RESET\s*\|\s*bool[^#\n]*$',  # list item with MODE_RESET | bool (not commented)
                    task_block
                )
                when_array = re.search(
                    r'(?m)^(?<!#)\s*when:\s*\[[^\]\n]*MODE_RESET\s*\|\s*bool[^\]\n]*\]',
                    task_block
                )

                when_ok = bool(when_inline or when_list or when_array)

                self.assertTrue(
                    when_ok,
                    (
                        f"Role '{role_name}': file '{include_fp}' must guard the reset include "
                        f"with a non-commented 'when' containing 'MODE_RESET | bool'. "
                        f"Commented-out conditions do not count."
                    )
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)
