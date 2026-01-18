# cli/deploy/test/storage.py
from __future__ import annotations

from .compose import Compose


def detect_storage_constrained(compose: Compose, *, threshold_gib: int = 100) -> bool:
    """
    Return True if the filesystem that contains DockerRootDir has less than
    `threshold_gib` GiB free space.

    We intentionally measure the DockerRootDir filesystem because this is where
    images/volumes/build cache usually grow (especially in CI / Docker-in-Docker).
    """
    threshold_bytes = threshold_gib * 1024 * 1024 * 1024

    cmd = [
        "sh",
        "-lc",
        r"""
set -euo pipefail
root="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || true)"
if [ -z "${root}" ]; then
  root="/var/lib/docker"
fi

free="$(df -PB1 "${root}" | awk 'NR==2{print $4}')"
printf "%s\n" "${free}"
""",
    ]

    r = compose.exec(cmd, check=False, capture=True)
    if r.returncode != 0:
        # If we can't determine free space, do not force constrained mode.
        return False

    txt = (r.stdout or "").strip()
    try:
        free_bytes = int(txt)
    except ValueError:
        return False

    return free_bytes < threshold_bytes
