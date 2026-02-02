# cli/deploy/development/mirrors.py
from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Dict


CONTAINER_REPO_ROOT = Path("/opt/src/infinito")


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if val is None or not str(val).strip():
        raise RuntimeError(f"Required environment variable is missing or empty: {name}")
    return str(val).strip()


def _require_bool_env(name: str) -> bool:
    raw = _require_env(name)
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise RuntimeError(
        f"Environment variable {name} must be 'true' or 'false', got {raw!r}"
    )


def should_use_mirrors_on_ci() -> bool:
    """
    Mirrors are enabled strictly based on RUNNING_ON_GITHUB.
    """
    return _require_bool_env("RUNNING_ON_GITHUB")


def _exec_env() -> Dict[str, str]:
    """
    All variables are mandatory. No fallbacks.
    """
    return {
        "RUNNING_ON_GITHUB": _require_env("RUNNING_ON_GITHUB"),
        "GITHUB_REPOSITORY_OWNER": _require_env("GITHUB_REPOSITORY_OWNER"),
        "INFINITO_GHCR_MIRROR_PREFIX": _require_env("INFINITO_GHCR_MIRROR_PREFIX"),
    }


def generate_ci_mirrors_file(compose, *, inventory_dir: str) -> str:
    """
    Generate mirrors.yml inside the container using cli.mirror.resolver.

    Writes:
      <inventory_dir>/mirrors.yml
    """
    inv_root = str(inventory_dir).rstrip("/")
    if not inv_root:
        raise RuntimeError("inventory_dir must not be empty")

    env = _exec_env()
    ghcr_namespace = env["GITHUB_REPOSITORY_OWNER"]
    ghcr_prefix = env["INFINITO_GHCR_MIRROR_PREFIX"].strip().strip("/")
    if not ghcr_prefix:
        raise RuntimeError("INFINITO_GHCR_MIRROR_PREFIX must not be empty")

    mirrors_path = f"{inv_root}/mirrors.yml"
    repo_root = str(CONTAINER_REPO_ROOT)

    cmd = [
        "sh",
        "-lc",
        "set -euo pipefail; "
        f"mkdir -p {shlex.quote(inv_root)}; "
        f"python3 -m cli.mirror.resolver "
        f"--repo-root {shlex.quote(repo_root)} "
        f"--ghcr-namespace {shlex.quote(ghcr_namespace)} "
        f"--ghcr-prefix {shlex.quote(ghcr_prefix)} "
        f"> {shlex.quote(mirrors_path)}; "
        f"echo '[init] mirrors generated:' {shlex.quote(mirrors_path)}; "
        f"wc -l {shlex.quote(mirrors_path)}",
    ]

    compose.exec(
        cmd,
        check=True,
        workdir=repo_root,
        extra_env=env,
    )

    return mirrors_path
