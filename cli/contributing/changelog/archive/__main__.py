"""Trim ``CHANGELOG.md`` to the last N entries and archive each older
release as its own file under ``docs/changelog/``.

Run via::

    python -m cli.contributing.changelog.archive [--keep N] [--dry-run]

Behaviour
---------

* Splits ``CHANGELOG.md`` by ``## [<version>] - <date>`` headers.
* Keeps the first ``N`` entries (default ``7``) in place.
* Writes every remaining release to its own file under
  ``docs/changelog/`` named ``<padded-semver>-<date>.md`` where
  ``<padded-semver>`` zero-pads each numeric component to three digits
  (``7.0.0`` becomes ``007.000.000``) and ``<date>`` is the
  ``YYYY-MM-DD`` value parsed from the version header.
* Replaces (or adds) an ``## Older Releases`` section at the bottom of
  the trimmed ``CHANGELOG.md`` that lists every archive file under
  ``docs/changelog/`` sorted descending by filename, so the newest
  archived release appears first.

The script is idempotent: re-running on a freshly trimmed
``CHANGELOG.md`` is a no-op when the entry count is already at or
below the threshold. Existing archive files are NOT overwritten.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cli import PROJECT_ROOT

_VERSION_HEADER_RE = re.compile(
    r"^## \[(?P<version>[^\]]+)\] - (?P<date>\S+)\s*$",
    re.MULTILINE,
)
_ARCHIVE_HEADER_RE = re.compile(r"^## (?:Older Releases|Archive)\s*$", re.MULTILINE)
_ARCHIVE_FILENAME_RE = re.compile(
    r"^\d{3}\.\d{3}\.\d{3}(?:[-+][^.]+)?-\d{4}-\d{2}-\d{2}\.md$"
)
_NUMERIC_COMPONENT_RE = re.compile(r"^\d+$")

_DEFAULT_KEEP = 7
_DEFAULT_ARCHIVE_DIR = "docs/changelog"


def _pad_version(version: str) -> str:
    """Zero-pad each numeric component of *version* to three digits.

    ``7.0.0`` → ``007.000.000``. A pre-release / build suffix
    (``1.2.3-rc1``, ``1.2.3+meta``) is preserved verbatim and tacked
    onto the padded core version.
    """
    parts = re.split(r"([-+])", version, maxsplit=1)
    core = parts[0]
    sep = parts[1] if len(parts) > 1 else ""
    suffix = parts[2] if len(parts) > 2 else ""
    padded = ".".join(
        c.zfill(3) if _NUMERIC_COMPONENT_RE.match(c) else c for c in core.split(".")
    )
    return f"{padded}{sep}{suffix}"


def _archive_filename(version: str, date: str) -> str:
    return f"{_pad_version(version)}-{date}.md"


def _split_into_entries(
    content: str,
) -> tuple[list[tuple[str, str, str]], str]:
    """Split *content* by version headers.

    Returns ``(entries, trailing)`` where ``entries`` is a list of
    tuples ``(version, date, body)`` (body starts with the
    ``## [version] - date`` header and ends just before the next
    version header) and ``trailing`` is everything after the last
    version entry that opens with an archive header (typically the
    ``## Older Releases`` index from a previous run); empty when no
    such tail is present.
    """
    matches = list(_VERSION_HEADER_RE.finditer(content))
    if not matches:
        return [], content

    entries: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end]
        entries.append((m.group("version"), m.group("date"), body))

    last_version, last_date, last_body = entries[-1]
    archive_match = _ARCHIVE_HEADER_RE.search(last_body)
    if archive_match is None:
        return entries, ""
    cut = archive_match.start()
    entries[-1] = (last_version, last_date, last_body[:cut])
    return entries, last_body[cut:]


def _existing_archives(archive_dir: Path) -> list[Path]:
    if not archive_dir.is_dir():
        return []
    return sorted(
        (
            p
            for p in archive_dir.iterdir()
            if p.is_file() and _ARCHIVE_FILENAME_RE.match(p.name)
        ),
        reverse=True,
    )


def _build_index_section(archive_dir: Path, repo_root: Path) -> str:
    archives = _existing_archives(archive_dir)
    if not archives:
        return ""
    lines = ["## Older Releases", ""]
    for path in archives:
        rel = path.relative_to(repo_root).as_posix()
        lines.append(f"- [{path.name}]({rel})")
    return "\n".join(lines) + "\n"


def trim_and_archive(
    changelog_path: Path,
    archive_dir: Path,
    repo_root: Path,
    *,
    keep: int = _DEFAULT_KEEP,
    dry_run: bool = False,
) -> tuple[int, list[Path]]:
    """Trim *changelog_path* to *keep* entries; archive every older
    release as its own file under *archive_dir*.

    Returns ``(kept, archive_paths)``. When fewer entries than *keep*
    exist, returns ``(n, [])`` and leaves the file untouched.
    """
    content = changelog_path.read_text(encoding="utf-8")
    entries, _existing_trailing = _split_into_entries(content)
    if len(entries) <= keep:
        return len(entries), []

    keep_entries = entries[:keep]
    archive_entries = entries[keep:]
    archive_paths: list[Path] = [
        archive_dir / _archive_filename(version, date)
        for version, date, _body in archive_entries
    ]

    if dry_run:
        return len(keep_entries), archive_paths

    archive_dir.mkdir(parents=True, exist_ok=True)
    for (version, date, body), target in zip(
        archive_entries, archive_paths, strict=True
    ):
        if target.exists():
            continue
        header = f"# {version} ({date})\n\n"
        target.write_text(header + body.rstrip() + "\n", encoding="utf-8")

    keep_text = "".join(body for _v, _d, body in keep_entries).rstrip()
    index_section = _build_index_section(archive_dir, repo_root)
    new_content = keep_text + "\n\n" + index_section
    changelog_path.write_text(new_content, encoding="utf-8")

    return len(keep_entries), archive_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cli.contributing.changelog.archive",
        description=(
            "Trim CHANGELOG.md to the last N entries (default 7) and "
            "archive each older release as its own file "
            "<padded-semver>-<date>.md under docs/changelog/."
        ),
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=_DEFAULT_KEEP,
        help=f"Number of recent entries to keep (default: {_DEFAULT_KEEP}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without modifying any file.",
    )
    args = parser.parse_args(argv)

    if args.keep < 1:
        parser.error("--keep MUST be >= 1")

    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    archive_dir = PROJECT_ROOT / _DEFAULT_ARCHIVE_DIR
    if not changelog_path.is_file():
        print(f"[ERR] CHANGELOG not found: {changelog_path}", file=sys.stderr)
        return 1

    kept, archive_paths = trim_and_archive(
        changelog_path,
        archive_dir,
        PROJECT_ROOT,
        keep=args.keep,
        dry_run=args.dry_run,
    )

    if not archive_paths:
        print(
            f"Nothing to archive: {kept} entries already at or below the "
            f"threshold of {args.keep}."
        )
        return 0

    verb = "would write" if args.dry_run else "wrote"
    print(f"{kept} kept; {verb} {len(archive_paths)} archive file(s):")
    for path in archive_paths:
        print(f"  - {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
