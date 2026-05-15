"""Check git `ref:` values in `roles/*/meta/services.yml`.

For every entity (at any depth — top-level entity, sub-entity, plugin
map) that declares BOTH `repository:` and `ref:`, and whose `ref:` is
a semver-compatible tag, this test fetches the upstream repository's
git tags via ``git ls-remote --tags <repository>`` and warns when a
newer semver tag exists.

Counterpart to ``tests/external/docker/test_image_versions.py`` —
that one bumps OCI image tags, this one bumps git refs for
from-source builds (plus plugin / build-helper / bootstrap repos).

External test: depends on live ``git ls-remote`` calls against the
remotes declared in services.yml. The test always passes so normal
validation stays stable even when remotes are slow or unreachable;
outdated refs surface as warnings on stdout and as GitHub Actions
``::warning::`` annotations on the offending services.yml line.

Suppress a check by placing ``# nocheck: repository-version`` on the
line directly above the ``ref:`` key (blank lines between are
ignored). Non-semver refs (`master`, `main`, `stable`, commit SHAs,
…) are skipped automatically — only refs that match
``utils.docker.version_updater.is_semver`` are checked.
"""

from __future__ import annotations

import subprocess
import unittest
from typing import TYPE_CHECKING

from utils.annotations.message import warning
from utils.annotations.suppress import is_suppressed_at
from utils.cache.files import read_text
from utils.cache.yaml import load_yaml_any
from utils.docker.version_updater import (
    is_semver,
    latest_semver,
    version_depth,
    version_flavor,
    version_key,
)
from utils.roles.mapping import ROLE_FILE_META_SERVICES

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_ROLES_ROOT = PROJECT_ROOT / "roles"
_NOCHECK_MARKER = "repository-version"


def _walk_repo_ref_pairs(node, path: list[str]) -> Iterator[tuple[list[str], str, str]]:
    """Yield ``(entity_path, repository, ref)`` for every dict in the
    tree that declares both keys with truthy string values."""
    if isinstance(node, dict):
        repo = node.get("repository")
        ref = node.get("ref")
        if isinstance(repo, str) and repo and isinstance(ref, str) and ref:
            yield (list(path), repo.strip(), ref.strip())
        for key, value in node.items():
            if key in ("repository", "ref"):
                continue
            yield from _walk_repo_ref_pairs(value, [*path, str(key)])
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk_repo_ref_pairs(item, [*path, f"[{index}]"])


def _suppressed_ref_paths(config_path: Path) -> set[tuple[int, int]]:
    """Return ``(start_line, indent)`` pairs whose `ref:` line is
    annotated with ``# nocheck: repository-version`` on the immediately
    preceding line. Paired with ``_locate_ref_lines`` to match entities."""
    raw = read_text(str(config_path))
    lines = raw.splitlines()
    suppressed: set[tuple[int, int]] = set()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith(("ref:", "ref :")):
            continue
        if is_suppressed_at(lines, index + 1, _NOCHECK_MARKER, mode="line-above"):
            indent = len(line) - len(stripped)
            suppressed.add((index + 1, indent))
    return suppressed


def _locate_ref_line(config_path: Path, ref_value: str) -> int | None:
    """Return the 1-indexed line number of the `ref: <value>` declaration
    in *config_path* whose value matches *ref_value*. Returns ``None``
    when no exact match is found (best-effort annotation anchor)."""
    raw = read_text(str(config_path))
    for index, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith(("ref:", "ref :")):
            continue
        try:
            _, value = stripped.split(":", 1)
        except ValueError:
            continue
        value = value.strip().strip("'\"")
        if value == ref_value:
            return index
    return None


def _git_ls_remote_tags(url: str) -> list[str]:
    """Return semver-compatible tag names from ``git ls-remote --tags``.
    Stripped of the ``refs/tags/`` prefix and ``^{}`` peeled-tag markers."""
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--tags", url],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    tags: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        name = parts[1]
        if not name.startswith("refs/tags/"):
            continue
        name = name[len("refs/tags/") :]
        name = name.removesuffix("^{}")
        if name:
            tags.add(name)
    return sorted(tags)


class TestRepositoryVersions(unittest.TestCase):
    """Warn about outdated semver `ref:` values in `meta/services.yml`."""

    def test_repository_refs_are_current(self) -> None:
        entries: list[dict] = []
        for role_dir in sorted(p for p in _ROLES_ROOT.iterdir() if p.is_dir()):
            services_path = role_dir / ROLE_FILE_META_SERVICES
            if not services_path.is_file():
                continue
            data = load_yaml_any(str(services_path), default_if_missing=None)
            if not isinstance(data, dict):
                continue
            suppressed = _suppressed_ref_paths(services_path)
            for entity_path, repo, ref in _walk_repo_ref_pairs(data, []):
                if not is_semver(ref):
                    continue
                line_no = _locate_ref_line(services_path, ref)
                if line_no and any(line_no == sl for sl, _ in suppressed):
                    continue
                entries.append(
                    {
                        "role": role_dir.name,
                        "entity": ".".join(entity_path),
                        "repository": repo,
                        "ref": ref,
                        "config_path": str(services_path.relative_to(PROJECT_ROOT)),
                        "line": line_no,
                    }
                )

        # Deduplicate `git ls-remote` calls per repository.
        repo_tags: dict[str, list[str]] = {}
        for entry in entries:
            url = entry["repository"]
            if url in repo_tags:
                continue
            repo_tags[url] = _git_ls_remote_tags(url)

        outdated: list[dict] = []
        unchecked: list[dict] = []
        for entry in entries:
            tags = repo_tags.get(entry["repository"], [])
            if not tags:
                unchecked.append(entry)
                continue
            latest = latest_semver(
                tags,
                version_depth(entry["ref"]),
                version_flavor(entry["ref"]),
            )
            if latest and version_key(entry["ref"]) < version_key(latest):
                outdated.append({**entry, "latest": latest})

        if outdated:
            col_w = (28, 30, 50, 12)
            header = (
                f"{'Role':<{col_w[0]}} {'Entity':<{col_w[1]}} "
                f"{'Repository':<{col_w[2]}} {'Current':<{col_w[3]}} Latest"
            )
            rows = "\n".join(
                f"{o['role']:<{col_w[0]}} {o['entity']:<{col_w[1]}} "
                f"{o['repository']:<{col_w[2]}} {o['ref']:<{col_w[3]}} {o['latest']}"
                for o in outdated
            )
            print(
                f"\n⚠️  Outdated repository refs:\n{header}\n{'-' * 140}\n{rows}\n"
                f"\n💡 To suppress a warning add above the ref: key:\n"
                f"  # nocheck: repository-version"
            )
            for o in outdated:
                msg = (
                    f"{o['role']}/{o['entity']}: {o['repository']} is at "
                    f"{o['ref']}, latest semver tag is {o['latest']}"
                )
                warning(
                    msg,
                    title="Outdated repository ref",
                    file=o["config_path"],
                    line=o["line"],
                )

        if unchecked:
            col_w = (28, 30, 50)
            header = (
                f"{'Role':<{col_w[0]}} {'Entity':<{col_w[1]}} "
                f"{'Repository':<{col_w[2]}} Current"
            )
            rows = "\n".join(
                f"{o['role']:<{col_w[0]}} {o['entity']:<{col_w[1]}} "
                f"{o['repository']:<{col_w[2]}} {o['ref']}"
                for o in unchecked
            )
            print(
                f"\n🔍 Unchecked repository refs (remote unreachable or no tags):\n"
                f"{header}\n{'-' * 130}\n{rows}"
            )
            for o in unchecked:
                msg = (
                    f"{o['role']}/{o['entity']}: {o['repository']} ref "
                    f"{o['ref']} could not be checked (remote unreachable)"
                )
                warning(
                    msg,
                    title="🔍 Unchecked repository ref",
                    file=o["config_path"],
                    line=o["line"],
                )

        # Always pass — outdated refs are warnings, not hard failures.
        self.assertIsNotNone(entries)


if __name__ == "__main__":
    unittest.main()
