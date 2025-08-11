# tests/integration/test_no_module_redirections_in_logs.py
import os
import glob
import re
import unittest
from collections import defaultdict

REDIR_RE = re.compile(r"redirecting \(type: modules\)\s+(\S+)\s+to\s+(\S+)", re.IGNORECASE)

class ModuleRedirectionLogTest(unittest.TestCase):
    """
    Fail if logs/*.log contains Ansible module redirections like:
      'redirecting (type: modules) ansible.builtin.pacman to community.general.pacman'
    Rationale: These lookups add overhead and clutter logs. Use fully-qualified
    collection names directly in tasks to improve performance and clarity.
    """

    def test_no_module_redirections(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        log_glob = os.path.join(project_root, "logs", "*.log")
        files = sorted(glob.glob(log_glob))

        if not files:
            self.skipTest(f"No log files found at {log_glob}")

        hits = []
        mappings = defaultdict(int)

        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for lineno, line in enumerate(fh, 1):
                        m = REDIR_RE.search(line)
                        if m:
                            src, dst = m.group(1), m.group(2)
                            hits.append((path, lineno, src, dst, line.strip()))
                            mappings[(src, dst)] += 1
            except OSError as e:
                self.fail(f"Cannot read log file {path}: {e}")

        if hits:
            # Build helpful failure message
            suggestions = []
            regex_hints = []
            for (src, dst), count in sorted(mappings.items(), key=lambda x: (-x[1], x[0])):
                suggestions.append(f"- Replace '{src}' with '{dst}' in your tasks ({count} occurrences).")
                # Create VS Code regex for finding these in YAML
                src_name = re.escape(src.split('.')[-1])  # only short module name
                regex_hints.append(f"(?<!{re.escape(dst.rsplit('.',1)[0])}\\.){src_name}:")

            examples = []
            for i, (path, lineno, src, dst, text) in enumerate(hits[:10], 1):
                examples.append(f"{i:02d}. {path}:{lineno}: {text}")

            msg = (
                f"Found {len(hits)} Ansible module redirections in logs/*.log.\n"
                f"These slow down execution and clutter logs. "
                f"Use fully-qualified module names to avoid runtime redirection.\n\n"
                f"Suggested replacements:\n"
                + "\n".join(suggestions)
                + "\n\nExamples:\n"
                + "\n".join(examples)
                + "\n\nVS Code regex to find each occurrence in your code:\n"
                + "\n".join(f"- {hint}" for hint in sorted(set(regex_hints)))
                + "\n\nExample fix:\n"
                f"  # Instead of:\n"
                f"  pacman:\n"
                f"  # Use:\n"
                f"  community.general.pacman:\n"
            )
            self.fail(msg)
