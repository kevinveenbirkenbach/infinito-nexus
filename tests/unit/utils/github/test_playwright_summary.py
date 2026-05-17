"""Unit tests for :mod:`utils.github.playwright_summary`.

Synthetic JUnit XML fixtures are produced under a tempdir so the real
project tree is never touched. Coverage spans the small pure helpers
(``_first_line``, ``_md_escape_cell``), the parser (``_extract_records``,
``_summarize_file``), the renderer (``_render``), and the CLI entry
point (``main``), including the three early-exit branches for missing
directories / no junit files / unparseable junit files.
"""

from __future__ import annotations

import io
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from utils.github import playwright_summary as ps

_TWO_SUITES_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="0" failures="0" skipped="0" time="0">
  <testsuite name="suite-a" tests="2" failures="1" skipped="0" time="3.5">
    <testcase name="passes" time="1.0"/>
    <testcase name="fails on assertion" time="2.5">
      <failure message="expected 1 got 0">stack-line-1\nstack-line-2</failure>
    </testcase>
  </testsuite>
  <testsuite name="suite-b" tests="2" failures="0" skipped="1" time="0.5">
    <testcase name="another pass" time="0.5"/>
    <testcase name="skipped one" time="0">
      <skipped message="persona blocked by env"/>
    </testcase>
  </testsuite>
</testsuites>"""

_ERROR_INSTEAD_OF_FAILURE_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite-c" time="1.0">
    <testcase name="crashes" time="1.0">
      <error message="ENOENT">no such file</error>
    </testcase>
  </testsuite>
</testsuites>"""


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestFormatDuration(unittest.TestCase):
    def test_sub_second_keeps_decimal(self) -> None:
        self.assertEqual(ps._format_duration(0.0), "0.0s")
        self.assertEqual(ps._format_duration(0.3), "0.3s")
        self.assertEqual(ps._format_duration(0.04), "0.0s")

    def test_sub_minute_keeps_decimal(self) -> None:
        self.assertEqual(ps._format_duration(12.5), "12.5s")
        self.assertEqual(ps._format_duration(59.9), "59.9s")

    def test_minute_boundary_rounds_seconds(self) -> None:
        self.assertEqual(ps._format_duration(60), "1m 0s")
        self.assertEqual(ps._format_duration(83.4), "1m 23s")
        self.assertEqual(ps._format_duration(3600), "60m 0s")


class TestFirstLine(unittest.TestCase):
    def test_none_returns_empty(self) -> None:
        self.assertEqual(ps._first_line(None), "")

    def test_whitespace_only_returns_empty(self) -> None:
        self.assertEqual(ps._first_line("   \n\t  "), "")

    def test_extracts_first_logical_line(self) -> None:
        self.assertEqual(
            ps._first_line("expected 1 got 0\nat /spec/foo.js:42"),
            "expected 1 got 0",
        )
        self.assertEqual(ps._first_line("  padded line  "), "padded line")


class TestMdEscapeCell(unittest.TestCase):
    def test_pipe_is_escaped(self) -> None:
        self.assertEqual(ps._md_escape_cell("a|b|c"), "a\\|b\\|c")

    def test_newlines_collapse_to_spaces(self) -> None:
        self.assertEqual(ps._md_escape_cell("line1\nline2"), "line1 line2")


class TestExtractRecords(unittest.TestCase):
    def test_mixed_pass_fail_skip(self) -> None:
        cases = list(
            ET.fromstring(_TWO_SUITES_FIXTURE).findall(".//testcase")  # noqa: S314 — fixture is hard-coded above
        )
        records = ps._extract_records(cases)
        self.assertEqual(
            records,
            [
                ("passes", "passed", "", 1.0),
                ("fails on assertion", "failed", "expected 1 got 0", 2.5),
                ("another pass", "passed", "", 0.5),
                ("skipped one", "skipped", "persona blocked by env", 0.0),
            ],
        )

    def test_error_child_counts_as_failed(self) -> None:
        cases = list(
            ET.fromstring(_ERROR_INSTEAD_OF_FAILURE_FIXTURE).findall(".//testcase")  # noqa: S314 — fixture is hard-coded above
        )
        records = ps._extract_records(cases)
        self.assertEqual(records, [("crashes", "failed", "ENOENT", 1.0)])

    def test_failure_with_only_text_uses_text(self) -> None:
        case = ET.fromstring(  # noqa: S314 — fixture literal, not user input
            '<testcase name="t"><failure>boom\nstack</failure></testcase>'
        )
        records = ps._extract_records([case])
        self.assertEqual(records, [("t", "failed", "boom", 0.0)])

    def test_skipped_without_message_yields_empty_string(self) -> None:
        case = ET.fromstring(  # noqa: S314 — fixture literal, not user input
            '<testcase name="anonymous-skip"><skipped/></testcase>'
        )
        records = ps._extract_records([case])
        self.assertEqual(records, [("anonymous-skip", "skipped", "", 0.0)])

    def test_malformed_time_falls_back_to_zero(self) -> None:
        case = ET.fromstring(  # noqa: S314 — fixture literal, not user input
            '<testcase name="bad-time" time="bogus"/>'
        )
        records = ps._extract_records([case])
        self.assertEqual(records, [("bad-time", "passed", "", 0.0)])


class TestSummarizeFile(unittest.TestCase):
    def test_uses_parent_dir_as_label_and_extracts_records(self) -> None:
        with TemporaryDirectory() as tmp:
            xml_path = _write(
                Path(tmp) / "web-app-foo" / "playwright-junit.xml", _TWO_SUITES_FIXTURE
            )
            summary = ps._summarize_file(xml_path)
        assert summary is not None
        self.assertEqual(summary["label"], "web-app-foo")
        self.assertEqual(len(summary["records"]), 4)
        self.assertEqual(summary["records"][1][1], "failed")
        self.assertEqual(summary["records"][3][1], "skipped")
        # Durations come straight from each testcase's `time` attribute.
        self.assertAlmostEqual(summary["records"][0][3], 1.0)
        self.assertAlmostEqual(summary["records"][1][3], 2.5)

    def test_unparseable_returns_none(self) -> None:
        with TemporaryDirectory() as tmp:
            xml_path = _write(Path(tmp) / "x" / "playwright-junit.xml", "<broken")
            self.assertIsNone(ps._summarize_file(xml_path))

    def test_empty_testsuites_returns_none(self) -> None:
        with TemporaryDirectory() as tmp:
            xml_path = _write(
                Path(tmp) / "x" / "playwright-junit.xml",
                "<testsuites></testsuites>",
            )
            self.assertIsNone(ps._summarize_file(xml_path))


class TestRender(unittest.TestCase):
    def _summary(self, label: str, records: list[tuple[str, str, str, float]]) -> dict:
        return {"label": label, "records": records}

    def test_emits_one_row_per_test_with_status_emoji(self) -> None:
        out = ps._render(
            [
                self._summary(
                    "web-app-foo",
                    [
                        ("test pass", "passed", "", 0.3),
                        ("test fail", "failed", "boom", 12.4),
                        ("test skip", "skipped", "blocked", 0.0),
                    ],
                ),
            ],
            "web-app-foo",
        )
        self.assertIn("### 🎭 Playwright — web-app-foo", out)
        self.assertIn("| App | Test | Status | Duration | Message |", out)
        self.assertIn("| `web-app-foo` | test pass | 🟢 | 0.3s |  |", out)
        self.assertIn("| `web-app-foo` | test fail | 🔴 | 12.4s | boom |", out)
        self.assertIn("| `web-app-foo` | test skip | 🔵 | 0.0s | blocked |", out)

    def test_status_legend_is_emitted(self) -> None:
        out = ps._render([self._summary("foo", [("t", "passed", "", 1.0)])], "ctx")
        self.assertIn("🟢 passed", out)
        self.assertIn("🔴 failed", out)
        self.assertIn("🔵 skipped", out)

    def test_multiple_apps_grouped_in_single_table(self) -> None:
        out = ps._render(
            [
                self._summary("a", [("t1", "passed", "", 0.1)]),
                self._summary("b", [("t2", "failed", "x", 65.0)]),
            ],
            "",
        )
        self.assertTrue(out.startswith("### 🎭 Playwright\n"))
        self.assertIn("| `a` | t1 | 🟢 | 0.1s |  |", out)
        self.assertIn("| `b` | t2 | 🔴 | 1m 5s | x |", out)
        # Should have a single combined table, not two.
        self.assertEqual(out.count("| App | Test | Status | Duration | Message |"), 1)

    def test_message_is_truncated(self) -> None:
        long_msg = "x" * (ps._MAX_MSG_LEN + 50)
        out = ps._render(
            [self._summary("foo", [("name", "failed", long_msg, 1.0)])],
            "ctx",
        )
        truncated = "x" * ps._MAX_MSG_LEN + "…"
        self.assertIn(truncated, out)

    def test_pipes_in_name_and_message_are_escaped(self) -> None:
        out = ps._render(
            [
                self._summary(
                    "foo",
                    [('up{job="x|y"} == 1', "failed", "got 0|1", 1.0)],
                )
            ],
            "ctx",
        )
        self.assertIn('up{job="x\\|y"} == 1', out)
        self.assertIn("got 0\\|1", out)


class TestMain(unittest.TestCase):
    def _run(self, *argv: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(ps, "sys") as fake_sys:
            fake_sys.argv = ["playwright_summary.py", *argv]
            fake_sys.stdout = stdout
            fake_sys.stderr = stderr
            rc = ps.main()
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_missing_argv_returns_two(self) -> None:
        rc, out, err = self._run()
        self.assertEqual(rc, 2)
        self.assertIn("Usage", err)
        self.assertEqual(out, "")

    def test_nonexistent_dir_emits_friendly_note(self) -> None:
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent"
            rc, out, _err = self._run(str(missing), "web-app-foo")
        self.assertEqual(rc, 0)
        self.assertIn("does not exist", out)
        self.assertIn("web-app-foo", out)

    def test_empty_dir_emits_no_junit_note(self) -> None:
        with TemporaryDirectory() as tmp:
            rc, out, _err = self._run(tmp, "web-app-foo")
        self.assertEqual(rc, 0)
        self.assertIn("No `playwright-junit.xml` found", out)

    def test_all_unparseable_emits_failure_note(self) -> None:
        with TemporaryDirectory() as tmp:
            _write(Path(tmp) / "x" / "playwright-junit.xml", "<broken")
            rc, out, _err = self._run(tmp, "web-app-foo")
        self.assertEqual(rc, 0)
        self.assertIn("failed to parse", out)

    def test_happy_path_renders_table(self) -> None:
        with TemporaryDirectory() as tmp:
            _write(
                Path(tmp) / "web-app-foo" / "playwright-junit.xml",
                _TWO_SUITES_FIXTURE,
            )
            rc, out, _err = self._run(tmp, "web-app-foo")
        self.assertEqual(rc, 0)
        self.assertIn("### 🎭 Playwright — web-app-foo", out)
        self.assertIn("| `web-app-foo` | passes | 🟢 | 1.0s |  |", out)
        self.assertIn(
            "| `web-app-foo` | fails on assertion | 🔴 | 2.5s | expected 1 got 0 |",
            out,
        )
        self.assertIn(
            "| `web-app-foo` | skipped one | 🔵 | 0.0s | persona blocked by env |",
            out,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
