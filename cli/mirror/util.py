from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple
import yaml

from .model import ImageRef


DOCKER_HUB_PREFIXES = (
    "docker.io/",
    "registry-1.docker.io/",
    "index.docker.io/",
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f) or {}
    return obj if isinstance(obj, dict) else {}


def is_docker_hub_image(image: str) -> bool:
    """
    Docker Hub images are either:
      - implicit: postgres, postgis/postgis
      - explicit: docker.io/postgis/postgis
    """
    image = image.strip()
    if not image:
        return False

    first = image.split("/", 1)[0]

    if first in ("docker.io", "registry-1.docker.io", "index.docker.io"):
        return True

    # looks like registry host
    if "." in first or ":" in first:
        return False

    return True


def normalize_docker_hub(image: str) -> str:
    """
    Remove docker hub registry prefix if present.
    """
    image = image.strip()
    for prefix in DOCKER_HUB_PREFIXES:
        if image.startswith(prefix):
            return image[len(prefix) :]
    return image


def split_name_and_suffix(image: str) -> Tuple[str, str]:
    """
    Split image into base name and suffix:
      repo/name:tag   -> (repo/name, :tag)
      repo/name@sha.. -> (repo/name, @sha..)
      repo/name       -> (repo/name, "")
    """
    image = image.strip()

    if "@sha256:" in image:
        base, digest = image.split("@", 1)
        return base, f"@{digest}"

    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        return image[:last_colon], image[last_colon:]

    return image, ""


def docker_hub_source(image: str, version: str) -> str:
    """
    Build canonical docker hub source ref for skopeo.

    postgres + 16         -> library/postgres:16
    postgis/postgis + 17  -> postgis/postgis:17
    """
    image = normalize_docker_hub(image)
    base, _suffix = split_name_and_suffix(image)  # drop embedded tag/digest if present

    if "/" not in base:
        base = f"library/{base}"

    return f"{base}:{version}"


def canonical_image_name(image: str) -> str:
    """
    Canonical image name without registry and without tag/digest.
    Keeps docker-hub implicit name as-is (without adding 'library/').
    """
    image = normalize_docker_hub(image)
    base, _suffix = split_name_and_suffix(image)
    return base


def iter_role_images(repo_root: Path) -> Iterable[ImageRef]:
    roles_dir = repo_root / "roles"

    for config_file in roles_dir.glob("**/config/main.yml"):
        role_name = config_file.parent.parent.name
        data = load_yaml(config_file)

        docker = data.get("docker", {})
        services = docker.get("services", {})

        if not isinstance(services, dict):
            continue

        for service_name, service in services.items():
            if not isinstance(service, dict):
                continue

            image = (service.get("image") or "").strip()
            version = (service.get("version") or "").strip()

            if not image or not version:
                continue

            if not is_docker_hub_image(image):
                continue

            yield ImageRef(
                role=role_name,
                service=str(service_name),
                name=canonical_image_name(image),
                version=version,
                source=docker_hub_source(image, version),
            )
