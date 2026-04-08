"""Check Docker image versions in roles/web-*/config/main.yml.

For each service with a semver-compatible version tag the latest available
tag on Docker Hub is fetched and compared. Outdated versions are reported as
GitHub Actions ``::warning::`` annotations or plain stdout warnings.

The test always passes so that CI is not blocked. Developers are notified of
available updates via the warning output.

Semver-compatible version formats checked:
  x  /  x.x  /  x.x.x  /  x.x.x.x  (with optional leading ``v``)

Suppress a check by placing ``# nocheck: docker-version`` on the line
directly above the ``version:`` key (blank lines between are ignored,
but any non-comment line resets the search):

    # nocheck: docker-version
    version: "4.5"
"""

from __future__ import annotations

import json
import re
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from utils.annotations.message import warning
from urllib.parse import quote, urlencode

import yaml

from utils.docker_image_ref import (
    DOCKER_HUB_REGISTRIES,
    GHCR_REGISTRY,
    split_registry_and_name,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROLES_ROOT = _REPO_ROOT / "roles"

# Matches: 1 / 1.2 / 1.2.3 / 1.2.3.4 with optional leading "v"
_SEMVER_RE = re.compile(r"^v?\d+(\.\d+){0,3}$")

_NOCHECK_TAG = "# nocheck: docker-version"


def _is_semver(value: str) -> bool:
    return bool(_SEMVER_RE.match(str(value).strip()))


def _version_key(tag: str) -> tuple[int, ...]:
    """Normalised 4-tuple for version comparison."""
    v = str(tag).strip().lstrip("v")
    tup = tuple(int(x) for x in v.split("."))
    return tup + (0,) * (4 - len(tup))


def _is_dockerhub(image: str) -> bool:
    """Return True when *image* refers to a Docker Hub repository.

    Handles both plain names (``nginx``, ``gitea/gitea``) and the explicit
    ``docker.io/`` registry prefix.
    """
    parsed = split_registry_and_name(image)
    if parsed is None:
        return False
    registry, _name = parsed
    return registry is None or registry in DOCKER_HUB_REGISTRIES


def _dockerhub_repo(image: str) -> str:
    """Normalise a Docker Hub image reference to ``namespace/name``."""
    parsed = split_registry_and_name(image)
    if parsed is None:
        raise ValueError(f"Invalid Docker image reference: {image!r}")
    registry, name = parsed
    if registry is not None and registry not in DOCKER_HUB_REGISTRIES:
        raise ValueError(f"Image is not a Docker Hub reference: {image!r}")
    return name if "/" in name else f"library/{name}"


def _fetch_dockerhub_tags(image: str, max_pages: int = 5) -> list[str]:
    """Return tag names for a Docker Hub image (up to *max_pages* x 100)."""
    repo = _dockerhub_repo(image)
    tags: list[str] = []
    for page in range(1, max_pages + 1):
        url = (
            f"https://hub.docker.com/v2/repositories/{repo}/tags/"
            f"?page_size=100&page={page}"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "infinito-nexus-version-check"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 429:
                    time.sleep(2)
                    continue
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            break
        tags.extend(r["name"] for r in body.get("results", []))
        if not body.get("next"):
            break
    return tags


def _is_ghcr(image: str) -> bool:
    """Return True when *image* refers to a GitHub Container Registry repository."""
    parsed = split_registry_and_name(image)
    return parsed is not None and parsed[0] == GHCR_REGISTRY


def _ghcr_repo(image: str) -> str:
    """Return the validated repository path of a ghcr.io image."""
    parsed = split_registry_and_name(image)
    if parsed is None or parsed[0] != GHCR_REGISTRY:
        raise ValueError(f"Image is not a GHCR reference: {image!r}")
    return parsed[1]


def _fetch_ghcr_tags(image: str) -> list[str]:
    """Return tag names for a ghcr.io image using anonymous token flow."""
    name = _ghcr_repo(image)
    token_query = urlencode(
        {"scope": f"repository:{name}:pull", "service": GHCR_REGISTRY}
    )
    token_url = f"https://{GHCR_REGISTRY}/token?{token_query}"
    try:
        req = urllib.request.Request(
            token_url, headers={"User-Agent": "infinito-nexus-version-check"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_body = json.loads(resp.read().decode())
        token = token_body.get("token") or token_body.get("access_token")
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []

    if not token:
        return []

    tags_url = f"https://{GHCR_REGISTRY}/v2/{quote(name, safe='/')}/tags/list"
    req = urllib.request.Request(
        tags_url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "infinito-nexus-version-check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []

    return body.get("tags") or []


def _version_depth(tag: str) -> int:
    """Return the number of dot-separated segments in a version string."""
    return len(str(tag).strip().lstrip("v").split("."))


def _latest_semver(tags: list[str], depth: int) -> str | None:
    """Return the highest semver tag from *tags* that has exactly *depth* segments.

    This ensures that a configured ``version: "15"`` (depth 1) is only compared
    against other single-segment tags, ``version: "8.3"`` (depth 2) only against
    ``x.x`` tags, and so on.
    """
    candidates = [t for t in tags if _is_semver(t) and _version_depth(t) == depth]
    return max(candidates, key=_version_key, default=None)


def _suppressed_services(config_path: Path) -> set[str]:
    """Return service names whose ``version:`` line is preceded by the nocheck tag."""
    raw = config_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    # Collect 0-based line numbers of suppressed version: keys
    suppressed_lines: set[int] = set()
    for i, line in enumerate(lines):
        if not re.search(r"^\s+version\s*:", line):
            continue
        for j in range(i - 1, -1, -1):
            prev = lines[j].strip()
            if prev == _NOCHECK_TAG:
                suppressed_lines.add(i)
                break
            if prev and not prev.startswith("#"):
                break  # non-comment line resets the nocheck window

    if not suppressed_lines:
        return set()

    # Map suppressed line numbers to service names via YAML node tree
    root = yaml.compose(raw)
    if not isinstance(root, yaml.MappingNode):
        return set()

    names: set[str] = set()
    for key, val in root.value:
        if key.value != "compose" or not isinstance(val, yaml.MappingNode):
            continue
        for k2, v2 in val.value:
            if k2.value != "services" or not isinstance(v2, yaml.MappingNode):
                continue
            for svc_key, svc_val in v2.value:
                if not isinstance(svc_val, yaml.MappingNode):
                    continue
                for fk, _ in svc_val.value:
                    if fk.value == "version" and fk.start_mark.line in suppressed_lines:
                        names.add(svc_key.value)
    return names


def _collect_entries() -> list[dict]:
    """Collect (role, service, image, version, config_path) for semver versions."""
    entries: list[dict] = []
    for config_path in sorted(_ROLES_ROOT.glob("web-*/config/main.yml")):
        role = config_path.parts[-3]
        rel_path = str(config_path.relative_to(_REPO_ROOT))
        try:
            raw = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            continue
        suppressed = _suppressed_services(config_path)
        services = (data.get("compose") or {}).get("services") or {}
        for svc, conf in services.items():
            if svc in suppressed:
                continue
            if not isinstance(conf, dict):
                continue
            image = conf.get("image")
            version = conf.get("version")
            if not image or version is None:
                continue
            version = str(version).strip()
            if not _is_semver(version):
                continue
            entries.append(
                {
                    "role": role,
                    "service": svc,
                    "image": image,
                    "version": version,
                    "config_path": rel_path,
                }
            )
    return entries


def _emit_annotation(
    config_path: str,
    role: str,
    service: str,
    image: str,
    current: str,
    latest: str,
) -> None:
    msg = f"{role}/{service}: {image} is at {current}, latest semver tag is {latest}"
    warning(msg, title="Outdated Docker image", file=config_path)


def _emit_unchecked_annotation(
    config_path: str, role: str, service: str, image: str
) -> None:
    msg = (
        f"{role}/{service}: {image} version could not be checked "
        f"(registry not supported)"
    )
    warning(msg, title="🔍 Unchecked Docker image", file=config_path)


class TestDockerImageVersions(unittest.TestCase):
    """Warn about outdated Docker image versions in roles/web-*/config/main.yml."""

    def test_image_versions_are_current(self) -> None:
        entries = _collect_entries()
        self.assertTrue(entries, "No semver-versioned config entries found")

        # Deduplicate registry queries per image
        image_tags: dict[str, list[str]] = {}
        for e in entries:
            img = e["image"]
            if img in image_tags:
                continue
            if _is_dockerhub(img):
                image_tags[img] = _fetch_dockerhub_tags(img)
            elif _is_ghcr(img):
                image_tags[img] = _fetch_ghcr_tags(img)

        outdated: list[dict] = []
        unchecked: list[dict] = []
        for e in entries:
            img = e["image"]
            if not _is_dockerhub(img) and not _is_ghcr(img):
                unchecked.append(e)
                continue
            tags = image_tags.get(img, [])
            if not tags:
                unchecked.append(e)
                continue
            latest = _latest_semver(tags, _version_depth(e["version"]))
            if latest and _version_key(e["version"]) < _version_key(latest):
                outdated.append({**e, "latest": latest})

        if outdated:
            col_w = (35, 20, 40, 15)
            header = (
                f"{'Role':<{col_w[0]}} {'Service':<{col_w[1]}} "
                f"{'Image':<{col_w[2]}} {'Current':<{col_w[3]}} Latest"
            )
            rows = "\n".join(
                f"{o['role']:<{col_w[0]}} {o['service']:<{col_w[1]}} "
                f"{o['image']:<{col_w[2]}} {o['version']:<{col_w[3]}} {o['latest']}"
                for o in outdated
            )
            print(
                f"\n⚠️  Outdated Docker image versions:\n{header}\n{'-' * 120}\n{rows}\n\n💡 To suppress a warning add above the version: key:\n  # nocheck: docker-version"
            )
            for o in outdated:
                _emit_annotation(
                    o["config_path"],
                    o["role"],
                    o["service"],
                    o["image"],
                    o["version"],
                    o["latest"],
                )

        if unchecked:
            col_w = (35, 20, 40, 15)
            header = (
                f"{'Role':<{col_w[0]}} {'Service':<{col_w[1]}} "
                f"{'Image':<{col_w[2]}} Current"
            )
            rows = "\n".join(
                f"{o['role']:<{col_w[0]}} {o['service']:<{col_w[1]}} "
                f"{o['image']:<{col_w[2]}} {o['version']}"
                for o in unchecked
            )
            print(
                f"\n🔍 Unchecked Docker image versions (registry not supported):\n"
                f"{header}\n{'-' * 100}\n{rows}"
            )
            for o in unchecked:
                _emit_unchecked_annotation(
                    o["config_path"], o["role"], o["service"], o["image"]
                )

        # Always pass - outdated images are warnings, not hard failures
        self.assertIsNotNone(entries)


if __name__ == "__main__":
    unittest.main()
