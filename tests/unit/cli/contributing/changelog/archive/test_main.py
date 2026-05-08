"""Unit tests for `cli.contributing.changelog.archive`.

Covers the public library surface (``trim_and_archive`` plus the
helpers the CLI builds on) against synthetic CHANGELOG fixtures
written to a temporary directory.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import cli.contributing.changelog.archive.__main__ as cl


def _make_changelog(versions: list[tuple[str, str, str]]) -> str:
    """Build a synthetic CHANGELOG body. *versions* is a list of
    ``(version, date, bullet)`` triples; each triple becomes one
    ``## [version] - date`` section with a single bullet line.
    """
    sections = [f"## [{v}] - {d}\n* {bullet}\n" for v, d, bullet in versions]
    return "\n".join(sections)


class TestPadVersion(unittest.TestCase):
    def test_three_component_release(self) -> None:
        self.assertEqual(cl._pad_version("7.0.0"), "007.000.000")
        self.assertEqual(cl._pad_version("0.1.0"), "000.001.000")
        self.assertEqual(cl._pad_version("4.0.3"), "004.000.003")
        self.assertEqual(cl._pad_version("12.34.56"), "012.034.056")

    def test_pre_release_suffix_preserved(self) -> None:
        self.assertEqual(cl._pad_version("1.2.3-rc1"), "001.002.003-rc1")
        self.assertEqual(cl._pad_version("1.2.3+build.5"), "001.002.003+build.5")

    def test_archive_filename_schema(self) -> None:
        self.assertEqual(
            cl._archive_filename("7.0.0", "2026-05-08"),
            "007.000.000-2026-05-08.md",
        )


class TestSplitIntoEntries(unittest.TestCase):
    def test_no_version_headers_returns_empty(self) -> None:
        entries, trailing = cl._split_into_entries("just text\n")
        self.assertEqual(entries, [])
        self.assertEqual(trailing, "just text\n")

    def test_each_header_starts_a_new_entry(self) -> None:
        body = _make_changelog(
            [("2.0.0", "2026-01-02", "two"), ("1.0.0", "2026-01-01", "one")]
        )
        entries, trailing = cl._split_into_entries(body)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][0], "2.0.0")
        self.assertEqual(entries[0][1], "2026-01-02")
        self.assertTrue(entries[0][2].startswith("## [2.0.0]"))
        self.assertEqual(entries[1][0], "1.0.0")
        self.assertEqual(trailing, "")

    def test_existing_older_releases_section_split_off(self) -> None:
        body = (
            _make_changelog([("1.0.0", "2026-01-01", "one")])
            + "\n## Older Releases\n\n- [foo.md](docs/changelog/foo.md)\n"
        )
        entries, trailing = cl._split_into_entries(body)
        self.assertEqual(len(entries), 1)
        self.assertNotIn("Older Releases", entries[0][2])
        self.assertIn("Older Releases", trailing)


class _ArchiveCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.archive_dir = self.repo_root / "docs" / "changelog"
        self.changelog = self.repo_root / "CHANGELOG.md"


class TestTrimAndArchive(_ArchiveCase):
    def _write_changelog(self, n: int) -> list[tuple[str, str, str]]:
        versions = [
            (f"{i}.0.0", f"2026-01-{i:02d}", f"bullet-{i}") for i in range(n, 0, -1)
        ]
        self.changelog.write_text(_make_changelog(versions), encoding="utf-8")
        return versions

    def test_short_changelog_is_noop(self) -> None:
        self._write_changelog(3)
        before = self.changelog.read_text(encoding="utf-8")
        kept, paths = cl.trim_and_archive(
            self.changelog, self.archive_dir, self.repo_root, keep=7
        )
        self.assertEqual(kept, 3)
        self.assertEqual(paths, [])
        self.assertEqual(self.changelog.read_text(encoding="utf-8"), before)
        self.assertFalse(self.archive_dir.exists())

    def test_archives_older_releases_one_file_each(self) -> None:
        versions = self._write_changelog(10)
        kept, paths = cl.trim_and_archive(
            self.changelog, self.archive_dir, self.repo_root, keep=7
        )
        self.assertEqual(kept, 7)
        self.assertEqual(len(paths), 3)
        expected_names = [cl._archive_filename(v, d) for v, d, _ in versions[7:]]
        self.assertEqual([p.name for p in paths], expected_names)
        for path, (version, date, _) in zip(paths, versions[7:], strict=True):
            self.assertTrue(path.is_file())
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(f"# {version} ({date})\n"))
            self.assertIn(f"## [{version}] - {date}", content)

    def test_kept_changelog_links_archives_at_bottom(self) -> None:
        self._write_changelog(10)
        cl.trim_and_archive(self.changelog, self.archive_dir, self.repo_root, keep=7)
        new = self.changelog.read_text(encoding="utf-8")
        archive_pos = new.index("## Older Releases")
        last_kept = "## [4.0.0]"
        self.assertIn(last_kept, new)
        self.assertLess(new.index(last_kept), archive_pos)
        for archive in self.archive_dir.iterdir():
            self.assertIn(f"({(archive.relative_to(self.repo_root)).as_posix()})", new)

    def test_dry_run_writes_nothing(self) -> None:
        self._write_changelog(10)
        before = self.changelog.read_text(encoding="utf-8")
        kept, paths = cl.trim_and_archive(
            self.changelog,
            self.archive_dir,
            self.repo_root,
            keep=7,
            dry_run=True,
        )
        self.assertEqual(kept, 7)
        self.assertEqual(len(paths), 3)
        self.assertEqual(self.changelog.read_text(encoding="utf-8"), before)
        self.assertFalse(self.archive_dir.exists())

    def test_idempotent_second_run(self) -> None:
        self._write_changelog(10)
        cl.trim_and_archive(self.changelog, self.archive_dir, self.repo_root, keep=7)
        first = self.changelog.read_text(encoding="utf-8")
        kept, paths = cl.trim_and_archive(
            self.changelog, self.archive_dir, self.repo_root, keep=7
        )
        self.assertEqual(kept, 7)
        self.assertEqual(paths, [])
        self.assertEqual(self.changelog.read_text(encoding="utf-8"), first)

    def test_existing_archive_files_are_not_overwritten(self) -> None:
        versions = self._write_changelog(10)
        oldest_version, oldest_date, _ = versions[-1]
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        existing_path = self.archive_dir / cl._archive_filename(
            oldest_version, oldest_date
        )
        sentinel = "do-not-overwrite\n"
        existing_path.write_text(sentinel, encoding="utf-8")

        cl.trim_and_archive(self.changelog, self.archive_dir, self.repo_root, keep=7)
        self.assertEqual(existing_path.read_text(encoding="utf-8"), sentinel)

    def test_subsequent_run_appends_new_archive_and_relinks_all(self) -> None:
        self._write_changelog(10)
        cl.trim_and_archive(self.changelog, self.archive_dir, self.repo_root, keep=7)
        # Prepend a fresh release (most-recent at top, oldest at bottom).
        kept_text = self.changelog.read_text(encoding="utf-8")
        cut = kept_text.index("## Older Releases")
        new_release = "## [11.0.0] - 2026-02-01\n* fresh\n\n"
        self.changelog.write_text(
            new_release + kept_text[:cut].rstrip() + "\n\n" + kept_text[cut:],
            encoding="utf-8",
        )

        kept, paths = cl.trim_and_archive(
            self.changelog, self.archive_dir, self.repo_root, keep=7
        )
        self.assertEqual(kept, 7)
        self.assertEqual(len(paths), 1)
        # The newly displaced release was 4.0.0 (the 8th entry after the
        # prepended 11.0.0).
        self.assertEqual(paths[0].name, cl._archive_filename("4.0.0", "2026-01-04"))
        new_changelog = self.changelog.read_text(encoding="utf-8")
        # The new release is the top entry.
        self.assertTrue(new_changelog.startswith("## [11.0.0]"))
        # Every archive on disk is linked from the index.
        archives_on_disk = sorted(
            (p for p in self.archive_dir.iterdir() if p.is_file()),
            reverse=True,
        )
        self.assertEqual(len(archives_on_disk), 4)
        for archive in archives_on_disk:
            rel = archive.relative_to(self.repo_root).as_posix()
            self.assertIn(f"]({rel})", new_changelog)
        # Newest archive is listed before older ones.
        idx_positions = [
            new_changelog.index(archive.name) for archive in archives_on_disk
        ]
        self.assertEqual(idx_positions, sorted(idx_positions))

    def test_custom_keep_value(self) -> None:
        self._write_changelog(5)
        kept, paths = cl.trim_and_archive(
            self.changelog, self.archive_dir, self.repo_root, keep=2
        )
        self.assertEqual(kept, 2)
        self.assertEqual(len(paths), 3)


class TestArchiveFilenamePadding(unittest.TestCase):
    def test_filenames_sort_chronologically_by_version(self) -> None:
        versions = [
            ("0.1.0", "2025-12-09"),
            ("4.0.3", "2026-02-16"),
            ("10.2.0", "2026-06-01"),
        ]
        names = [cl._archive_filename(v, d) for v, d in versions]
        self.assertEqual(sorted(names), names)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
