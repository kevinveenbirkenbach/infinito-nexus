from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants (single source of truth)
# ---------------------------------------------------------------------------

CI_DOCKER_ROOT = Path("/mnt/docker")
CI_DOCKER_ROOT_STR = str(CI_DOCKER_ROOT)


def _base_env(*, distro: str) -> dict[str, str]:
    env = dict(os.environ)
    env["INFINITO_DISTRO"] = distro
    return env


def _compose_run(*, repo_root: Path, distro: str, args: list[str]) -> None:
    cmd = ["docker", "compose", "--profile", "ci", *args]
    subprocess.run(
        cmd,
        cwd=repo_root,
        env=_base_env(distro=distro),
        check=True,
        text=True,
    )


def _cleanup_docker_root() -> None:
    if os.environ.get("RUNNING_ON_GITHUB") != "true":
        return

    docker_root_env = os.environ.get("INFINITO_DOCKER_VOLUME", "").strip().rstrip("/")

    if docker_root_env and docker_root_env != CI_DOCKER_ROOT_STR:
        raise RuntimeError(
            "SECURITY VIOLATION: "
            f"INFINITO_DOCKER_VOLUME={docker_root_env} is not allowed on GitHub runner. "
            f"Only {CI_DOCKER_ROOT_STR} is permitted."
        )

    docker_root = CI_DOCKER_ROOT

    if not docker_root.exists():
        print(f">>> Docker root does not exist, nothing to clean: {docker_root}")
        return

    print(f">>> CI cleanup: wiping Docker root: {docker_root}")
    shutil.rmtree(docker_root, ignore_errors=True)
    docker_root.mkdir(parents=True, exist_ok=True)


def down_stack(*, repo_root: Path, distro: str) -> None:
    print(">>> Stopping compose stack and removing volumes")
    try:
        _compose_run(
            repo_root=repo_root,
            distro=distro,
            args=["down", "--remove-orphans", "-v"],
        )
    finally:
        _cleanup_docker_root()
