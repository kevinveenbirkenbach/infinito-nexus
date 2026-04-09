"""
Ensure all GHCR mirror packages are publicly visible.

Lists every container package under the given namespace that starts with
the mirror prefix, checks visibility, and sets any non-public package to
public via the GitHub Packages API.

Usage:
    python -m cli.mirror.publish --ghcr-namespace <org> [--ghcr-prefix mirror]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator

from utils.annotations.message import warning as gha_warning


class _InsufficientTokenError(Exception):
    """Raised when the supplied token cannot access the requested GitHub API endpoint."""


def _gh_get(url: str, token: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _resolve_account_type(namespace: str, token: str) -> str:
    """Return 'orgs' if namespace is a GitHub org, 'users' otherwise."""
    url = f"https://api.github.com/orgs/{namespace}/packages?package_type=container&per_page=1"
    try:
        _gh_get(url, token)
        return "orgs"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(
                f"[publish] '{namespace}' is not an org, using user account endpoint…",
                flush=True,
            )
            return "users"
        raise


def _list_packages(namespace: str, token: str, account_type: str) -> Iterator[dict]:
    """Yield all container packages for the namespace (handles pagination).

    For user accounts, uses /user/packages with an explicit visibility parameter
    because installation tokens (GITHUB_TOKEN) require it.  We query private and
    internal visibility separately to find all non-public packages.

    For org accounts, no visibility filter is needed.
    """
    if account_type == "orgs":
        bases = [f"https://api.github.com/orgs/{namespace}/packages"]
        visibility_params = [""]
    else:
        bases = ["https://api.github.com/user/packages"] * 2
        visibility_params = ["&visibility=private", "&visibility=internal"]

    for base, vis in zip(bases, visibility_params):
        page = 1
        while True:
            try:
                data = _gh_get(
                    f"{base}?package_type=container&per_page=100&page={page}{vis}",
                    token,
                )
            except urllib.error.HTTPError as e:
                if e.code in (400, 401, 403) and account_type == "users":
                    raise _InsufficientTokenError(
                        f"HTTP {e.code} when listing user packages"
                    ) from e
                raise
            if not data:
                break
            yield from data
            if len(data) < 100:
                break
            page += 1


def _set_public(
    namespace: str,
    pkg_name: str,
    token: str,
    account_type: str,
    *,
    retries: int = 5,
    retry_delay: float = 10.0,
) -> None:
    encoded = urllib.parse.quote(pkg_name, safe="")
    if account_type == "orgs":
        url = f"https://api.github.com/orgs/{namespace}/packages/container/{encoded}"
    else:
        url = f"https://api.github.com/user/packages/container/{encoded}"
    body = json.dumps({"visibility": "public"}).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req):
                return
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt < retries:
                print(
                    f"[publish] visibility update for '{pkg_name}' failed "
                    f"(attempt {attempt}/{retries}): {e} — retrying in {retry_delay}s…",
                    flush=True,
                )
                time.sleep(retry_delay)
            else:
                raise RuntimeError(
                    f"[publish] Failed to set '{pkg_name}' to public after {retries} attempts: {e}"
                ) from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set all GHCR mirror packages to public."
    )
    parser.add_argument(
        "--ghcr-namespace", required=True, help="GitHub org/user namespace"
    )
    parser.add_argument(
        "--ghcr-prefix", default="mirror", help="Package name prefix (default: mirror)"
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("[publish] ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        return 1

    namespace = args.ghcr_namespace.lower()
    prefix = args.ghcr_prefix.strip("/")

    failures: list[str] = []
    updated = 0
    skipped = 0

    account_type = _resolve_account_type(namespace, token)

    print(
        f"[publish] Scanning packages for '{namespace}' with prefix '{prefix}/'…",
        flush=True,
    )

    _GHCR_DOC_PATH = "docs/contributing/flow/security/ghcr.md"
    _server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    _repo = os.environ.get("GITHUB_REPOSITORY", "")
    _GHCR_DOC_URL = (
        f"{_server}/{_repo}/blob/master/{_GHCR_DOC_PATH}"
        if _repo
        else _GHCR_DOC_PATH
    )
    try:
        pkg_iter = list(_list_packages(namespace, token, account_type))
    except _InsufficientTokenError as e:
        gha_warning(
            f"Mirror visibility update skipped — {e}. "
            "The GITHUB_TOKEN is an installation token and cannot list packages for personal accounts. "
            "Set the GHCR_PAT secret to a classic PAT with read:packages and write:packages scopes. "
            f"See {_GHCR_DOC_URL} for setup instructions.",
            title="GHCR visibility update skipped — GHCR_PAT required",
        )
        return 0

    for pkg in pkg_iter:
        name: str = pkg.get("name", "")
        if not name.startswith(f"{prefix}/"):
            continue

        visibility: str = pkg.get("visibility", "")
        if visibility == "public":
            print(f"[publish] {name}: already public, skipping", flush=True)
            skipped += 1
            continue

        print(
            f"[publish] {name}: visibility={visibility!r} → setting public…", flush=True
        )
        try:
            _set_public(namespace, name, token, account_type)
            print(f"[publish] {name}: ✓ set to public", flush=True)
            updated += 1
        except RuntimeError as e:
            print(str(e), file=sys.stderr, flush=True)
            failures.append(name)

    print(
        f"\n[publish] Done: {updated} updated, {skipped} already public, {len(failures)} failed.",
        flush=True,
    )

    if failures:
        print("[publish] Failed packages:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
