import io
import os
import re
import unittest
from pathlib import Path


ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
CTRL_RE = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")

RUNNING_HANDLER_RE = re.compile(
    r"RUNNING HANDLER\s*\[(?P<role>[^:\]]+)\s*:\s*(?P<name>[^\]]+)\]"
)
TASK_BLOCK_START_RE = re.compile(r"\bTASK\s*\[")
TASK_PATH_HANDLERS_RE = re.compile(r"task path:\s*.+?/handlers/.+", re.IGNORECASE)

SKIP_FALSE_RE = re.compile(
    r'\bskipping:\s*\[.+?\].+?"skip_reason"\s*:\s*"Conditional result was False"',
    re.IGNORECASE,
)

#: Handlers in this whitelist are allowed to be skipped due to
#: "Conditional result was False" without failing the test.
#: Each entry is a tuple: (role_name, handler_name) as shown in the log
#: after "RUNNING HANDLER [role : name]".
WHITELISTED_HANDLERS = {
    # Example / current known exception:
    ("sys-daemon", "validate systemd units"),
    # Add further exceptions here, e.g.:
    # ("some-role", "some handler name"),
}


def clean_line(s: str) -> str:
    """Strip ANSI escape sequences and control characters from a log line."""
    s = ANSI_RE.sub("", s)
    s = CTRL_RE.sub("", s)
    return s.rstrip("\r\n")


class TestNoSkippedHandlers(unittest.TestCase):
    def test_handlers_not_skipped_due_to_false_conditions(self):
        # Use an env var if you have one, otherwise default to "logs"
        logs_dir = Path(os.environ.get("LOG_DIR", "logs"))
        self.assertTrue(
            logs_dir.exists(), f"Logs directory not found: {logs_dir.resolve()}"
        )

        log_files = sorted(logs_dir.glob("*.log"))
        if not log_files:
            self.skipTest(f"No .log files in {logs_dir.resolve()}")

        violations = []

        for lf in log_files:
            with io.open(lf, "r", encoding="utf-8", errors="ignore") as f:
                lines = [clean_line(x) for x in f]

            i = 0
            n = len(lines)

            while i < n:
                m = RUNNING_HANDLER_RE.search(lines[i])
                if not m:
                    i += 1
                    continue

                handler_idx = i
                handler_line = lines[i]

                # Extract handler identification for whitelist checking
                handler_role = m.group("role").strip()
                handler_name = m.group("name").strip()
                handler_id = (handler_role, handler_name)

                j = i + 1
                saw_handlers_task_path = False

                hard_cap = min(n, j + 400)

                while j < hard_cap:
                    # Stop scanning when a new handler or a new task block starts
                    if RUNNING_HANDLER_RE.search(lines[j]) or TASK_BLOCK_START_RE.search(
                        lines[j]
                    ):
                        break

                    if TASK_PATH_HANDLERS_RE.search(lines[j]):
                        saw_handlers_task_path = True

                    if SKIP_FALSE_RE.search(lines[j]) and saw_handlers_task_path:
                        # Ignore handlers that are explicitly whitelisted
                        if handler_id in WHITELISTED_HANDLERS:
                            # Allowed exception, do not record a violation
                            break

                        # Record violation for non-whitelisted handlers
                        violations.append(
                            (lf, handler_idx + 1, handler_line, j + 1, lines[j])
                        )
                        break

                    j += 1

                # Continue scanning from where we left off
                i = j

        if violations:
            report = [
                "Detected HANDLERs skipped due to false conditions (within handler blocks):"
            ]
            for lf, h_ln, h_txt, s_ln, s_txt in violations:
                report.append(
                    f"\nFile: {lf}\n"
                    f"  Handler @ line {h_ln}: {h_txt}\n"
                    f"  Skip    @ line {s_ln}: {s_txt}"
                )
            self.fail("\n".join(report))


if __name__ == "__main__":
    unittest.main()
