"""GitHub Actions workflow command annotations.

Outputs structured log messages that GitHub Actions renders as annotations
(warning triangles, error markers, etc.) in the job summary and log view.

See: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#setting-a-warning-message
"""

from __future__ import annotations

from typing import Iterable, Optional


def _emit(
    level: str,
    message: str,
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    col: Optional[int] = None,
) -> None:
    parts = []
    if title:
        parts.append(f"title={title}")
    if file:
        parts.append(f"file={file}")
    if line is not None:
        parts.append(f"line={line}")
    if col is not None:
        parts.append(f"col={col}")
    props = ",".join(parts)
    prefix = f"::{level} {props}::" if props else f"::{level}::"
    print(f"{prefix}{message}", flush=True)


def warning(
    message: str,
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    col: Optional[int] = None,
) -> None:
    _emit("warning", message, title=title, file=file, line=line, col=col)


def error(
    message: str,
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    col: Optional[int] = None,
) -> None:
    _emit("error", message, title=title, file=file, line=line, col=col)


def notice(
    message: str,
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    col: Optional[int] = None,
) -> None:
    _emit("notice", message, title=title, file=file, line=line, col=col)


def warning_each(
    items: Iterable[str],
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
) -> None:
    """Emit one warning annotation per item in *items*."""
    for item in items:
        warning(item, title=title, file=file)


def error_each(
    items: Iterable[str],
    *,
    title: Optional[str] = None,
    file: Optional[str] = None,
) -> None:
    """Emit one error annotation per item in *items*."""
    for item in items:
        error(item, title=title, file=file)
