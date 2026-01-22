from __future__ import annotations
from abc import ABC, abstractmethod
import subprocess

from .model import ImageRef


class RegistryProvider(ABC):
    @abstractmethod
    def image_base(self, image: ImageRef) -> str: ...

    @abstractmethod
    def mirror(self, image: ImageRef) -> None: ...


class GHCRProvider(RegistryProvider):
    def __init__(self, namespace: str, prefix: str = "mirror") -> None:
        self.namespace = namespace
        self.prefix = prefix.strip("/")

    def image_base(self, image: ImageRef) -> str:
        mapped = image.name.replace("/", "-")
        return f"ghcr.io/{self.namespace}/{self.prefix}/{mapped}"

    def mirror(self, image: ImageRef) -> None:
        dest = f"{self.image_base(image)}:{image.version}"
        src = f"docker://docker.io/{image.source}"
        subprocess.run(["skopeo", "copy", "--all", src, f"docker://{dest}"], check=True)


class GiteaProvider(RegistryProvider):
    def __init__(self, registry: str, namespace: str, prefix: str = "mirror") -> None:
        self.registry = registry.rstrip("/")
        self.namespace = namespace
        self.prefix = prefix.strip("/")

    def image_base(self, image: ImageRef) -> str:
        mapped = image.name.replace("/", "-")
        return f"{self.registry}/{self.namespace}/{self.prefix}/{mapped}"

    def mirror(self, image: ImageRef) -> None:
        dest = f"{self.image_base(image)}:{image.version}"
        src = f"docker://docker.io/{image.source}"
        subprocess.run(["skopeo", "copy", "--all", src, f"docker://{dest}"], check=True)
