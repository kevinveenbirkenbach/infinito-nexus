from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import yaml


DOCKER_HUB_PREFIXES = (
    "docker.io/",
    "registry-1.docker.io/",
    "index.docker.io/",
)


@dataclass(frozen=True)
class ImageRef:
    role: str  # e.g. svc-db-postgres
    service: str  # e.g. postgres
    name: str  # canonical image name without registry, e.g. postgis/postgis or postgres
    version: str  # e.g. 17-3.5
    source: str  # source ref for skopeo, e.g. library/postgres:16
    registry: str = "docker.io"  # source registry, e.g. docker.io or mcr.microsoft.com
    source_file: str = "config/main.yml"  # "config/main.yml" or "vars/main.yml"


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
    """Remove docker hub registry prefix if present."""
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

    postgres + 16        -> library/postgres:16
    postgis/postgis + 17 -> postgis/postgis:17
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


def _registry_of(image: str) -> str:
    """
    Return the registry host of an image reference.
    Docker Hub images (no dot/colon in first segment) return 'docker.io'.
    """
    first = image.strip().split("/", 1)[0]
    if "." in first or ":" in first:
        return first
    return "docker.io"


def iter_role_images(repo_root: Path) -> Iterable[ImageRef]:
    """
    Yield all ImageRef entries discovered across all roles in *repo_root*.

    Sources:
      1. roles/**/config/main.yml → compose.services.<svc>.{image,version}
      2. roles/**/vars/main.yml   → images.<name>.{image,version}
    """
    roles_dir = repo_root / "roles"

    # 1. Images from config/main.yml → compose.services (any registry)
    for config_file in roles_dir.glob("**/config/main.yml"):
        role_name = config_file.parent.parent.name
        data = load_yaml(config_file)

        docker = data.get("compose", {})
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

            registry = _registry_of(image)

            if registry == "docker.io":
                yield ImageRef(
                    role=role_name,
                    service=str(service_name),
                    name=canonical_image_name(image),
                    version=version,
                    source=docker_hub_source(image, version),
                    registry="docker.io",
                    source_file="config/main.yml",
                )
            else:
                base, _suffix = split_name_and_suffix(image)
                name = (
                    base[len(registry) + 1 :]
                    if base.startswith(registry + "/")
                    else base
                )
                yield ImageRef(
                    role=role_name,
                    service=str(service_name),
                    name=name,
                    version=version,
                    source=f"{image}:{version}",
                    registry=registry,
                    source_file="config/main.yml",
                )

    # 2. Non-Docker-Hub images from vars/main.yml → images.<name>.{image,version}
    for vars_file in roles_dir.glob("**/vars/main.yml"):
        role_name = vars_file.parent.parent.name
        data = load_yaml(vars_file)

        images = data.get("images", {})
        if not isinstance(images, dict):
            continue

        for service_name, entry in images.items():
            if not isinstance(entry, dict):
                continue

            image = (entry.get("image") or "").strip()
            version = (entry.get("version") or "").strip()

            if not image or not version:
                continue

            registry = _registry_of(image)
            base, _suffix = split_name_and_suffix(image)
            # Strip registry prefix from name so image_base() maps cleanly
            if registry != "docker.io" and base.startswith(registry + "/"):
                name = base[len(registry) + 1 :]
            else:
                name = base

            yield ImageRef(
                role=role_name,
                service=str(service_name),
                name=name,
                version=version,
                source=f"{image}:{version}",
                registry=registry,
                source_file="vars/main.yml",
            )
