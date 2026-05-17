"""Render Playwright JUnit XML reports as GitHub Actions step-summary markdown.

Walks the given directory, parses every ``playwright-junit.xml`` it finds,
and prints a markdown table with one row per test case (app, test title,
status, message) to stdout. The output is designed to be appended to
``$GITHUB_STEP_SUMMARY``.

Usage:
    python3 utils/github/playwright_summary.py <reports-dir> [<context-label>]  # nocheck: self-path-reference
"""

from __future__ import annotations

import contextlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Cap the message column at this length so a multi-kilobyte stack trace
# does not break the step-summary layout.
_MAX_MSG_LEN = 200

# Status indicators as requested: red / green / blue circles.
_STATUS_PASSED = "passed"
_STATUS_FAILED = "failed"
_STATUS_SKIPPED = "skipped"
_STATUS_EMOJI: dict[str, str] = {
    _STATUS_PASSED: "🟢",
    _STATUS_FAILED: "🔴",
    _STATUS_SKIPPED: "🔵",
}


def _format_duration(seconds: float) -> str:
    """Format ``seconds`` as ``0.3s`` / ``12.5s`` / ``2m 15s``.

    Sub-minute durations keep one decimal because many playwright tests
    run in well under a second; rounding them all to ``0s`` / ``1s``
    would hide useful per-test signal.
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = round(seconds % 60)
    return f"{m}m {s}s"


def _first_line(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    return text.splitlines()[0]


def _md_escape_cell(value: str) -> str:
    """Markdown-table-cell safe: escape pipes and collapse newlines."""
    return value.replace("|", "\\|").replace("\n", " ")


def _extract_records(cases: list[ET.Element]) -> list[tuple[str, str, str, float]]:
    """Return a ``(test_name, status, message, duration)`` tuple per testcase.

    Status is one of ``passed`` / ``failed`` / ``skipped``. Message is
    the first logical line of the JUnit ``<failure>`` / ``<error>`` /
    ``<skipped>`` element when present, else the empty string. Duration
    is the value of the JUnit ``time`` attribute in seconds; missing or
    unparseable values fall back to ``0.0``.
    """
    records: list[tuple[str, str, str, float]] = []
    for case in cases:
        name = case.get("name", "?")
        duration = 0.0
        with contextlib.suppress(ValueError, TypeError):
            duration = float(case.get("time", "0") or "0")
        fail = case.find("failure")
        if fail is None:
            fail = case.find("error")
        if fail is not None:
            msg = _first_line(fail.get("message") or fail.text)
            records.append((name, _STATUS_FAILED, msg, duration))
            continue
        skip = case.find("skipped")
        if skip is not None:
            msg = _first_line(skip.get("message") or skip.text)
            records.append((name, _STATUS_SKIPPED, msg, duration))
            continue
        records.append((name, _STATUS_PASSED, "", duration))
    return records


def _summarize_file(path: Path) -> dict | None:
    try:
        root = ET.parse(path).getroot()  # noqa: S314
    except ET.ParseError:
        return None
    cases: list[ET.Element] = []
    for suite in root.findall(".//testsuite"):
        cases.extend(suite.findall("testcase"))
    if not cases:
        return None
    return {
        "label": path.parent.name,
        "records": _extract_records(cases),
    }


def _render(summaries: list[dict], context: str) -> str:
    title = f"### 🎭 Playwright — {context}" if context else "### 🎭 Playwright"
    lines: list[str] = [
        title,
        "",
        "Status: 🟢 passed · 🔴 failed · 🔵 skipped",
        "",
        "| App | Test | Status | Duration | Message |",
        "|---|---|:---:|---:|---|",
    ]
    for s in summaries:
        for name, status, msg, duration in s["records"]:
            emoji = _STATUS_EMOJI.get(status, "❔")
            if msg:
                truncated = msg[:_MAX_MSG_LEN] + (
                    "…" if len(msg) > _MAX_MSG_LEN else ""
                )
                message_cell = _md_escape_cell(truncated)
            else:
                message_cell = ""
            lines.append(
                f"| `{s['label']}` | {_md_escape_cell(name)} | {emoji} | "
                f"{_format_duration(duration)} | {message_cell} |"
            )
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(f"Usage: {sys.argv[0]} <reports-dir> [<context-label>]\n")
        return 2
    base = Path(sys.argv[1])
    context = sys.argv[2] if len(sys.argv) > 2 else ""

    if not base.is_dir():
        sys.stdout.write(
            f"### 🎭 Playwright — {context or 'no reports'}\n\n"
            f"_Reports directory `{base}` does not exist; Playwright did not run._\n"
        )
        return 0

    # nocheck: project-walk — walks a CI artifact directory at runtime,
    # not the project tree; the `utils.cache.files` SPOT does not apply.
    files = sorted(base.rglob("playwright-junit.xml"))
    if not files:
        sys.stdout.write(
            f"### 🎭 Playwright — {context or 'no reports'}\n\n"
            f"_No `playwright-junit.xml` found under `{base}`._\n"
        )
        return 0

    summaries = [s for s in (_summarize_file(p) for p in files) if s]
    if not summaries:
        sys.stdout.write(
            f"### 🎭 Playwright — {context or 'unparseable'}\n\n"
            f"_All `playwright-junit.xml` files failed to parse._\n"
        )
        return 0

    sys.stdout.write(_render(summaries, context) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
