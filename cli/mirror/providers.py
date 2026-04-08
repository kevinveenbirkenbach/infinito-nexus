# cli/mirror/providers.py
from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from .model import ImageRef


class RegistryProvider(ABC):
    @abstractmethod
    def image_base(self, image: ImageRef) -> str:
        pass

    @abstractmethod
    def mirror(self, image: ImageRef) -> None:
        pass

    @abstractmethod
    def tag_exists(self, image: ImageRef) -> bool:
        pass

    def ensure_public(self, image: ImageRef) -> None:
        """Best-effort hook for registries that support package visibility."""
        return


class GHCRProvider(RegistryProvider):
    def __init__(self, namespace: str, prefix: str = "mirror") -> None:
        self.namespace = namespace.lower()
        self.prefix = prefix.strip("/")

    def image_base(self, image: ImageRef) -> str:
        mapped = image.name.replace("/", "-")
        return f"ghcr.io/{self.namespace}/{self.prefix}/{mapped}"

    def tag_exists(self, image: ImageRef) -> bool:
        """
        Return True if the destination tag already exists in GHCR.

        Uses: skopeo inspect docker://<dest>
        Exit code:
          - 0 => exists
          - !=0 => does not exist OR cannot be accessed (auth/network)
        """
        dest = f"{self.image_base(image)}:{image.version}"
        r = subprocess.run(
            ["skopeo", "inspect", f"docker://{dest}"],
            check=False,
            capture_output=True,
            text=True,
        )
        return r.returncode == 0

    def _run_copy(self, *, src: str, dest: str, extra: List[str] | None = None) -> None:
        cmd = [
            "skopeo",
            "copy",
            "--all",
            "--retry-times",
            "5",
            "--dest-precompute-digests",
        ]
        if extra:
            cmd += extra
        cmd += [src, f"docker://{dest}"]

        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )

    def _looks_like_blob_reuse_problem(self, e: subprocess.CalledProcessError) -> bool:
        out = (e.stdout or "") + "\n" + (e.stderr or "")
        s = out.lower()
        return (
            "reuse blob" in s
            or "blob mount" in s
            or "mount blob" in s
            or ("failed to mount" in s and ("403" in s or "401" in s))
            or "denied:" in s
            or "unauthorized" in s
        )

    def _set_public(self, image: ImageRef) -> None:
        """Set the GHCR package visibility to public via GitHub API."""
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("[mirror] WARNING: GITHUB_TOKEN not set, skipping visibility update", flush=True)
            return

        mapped = image.name.replace("/", "-")
        pkg = urllib.parse.quote(f"{self.prefix}/{mapped}", safe="")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        body = json.dumps({"visibility": "public"}).encode()

        errors = []
        for url in [
            f"https://api.github.com/users/{self.namespace}/packages/container/{pkg}",
            f"https://api.github.com/orgs/{self.namespace}/packages/container/{pkg}",
        ]:
            req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
            try:
                with urllib.request.urlopen(req):
                    return
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                errors.append(f"{url}: {e}")

        raise RuntimeError(
            f"[mirror] Failed to set package visibility to public for '{pkg}':\n"
            + "\n".join(errors)
        )

    def ensure_public(self, image: ImageRef) -> None:
        self._set_public(image)

    def mirror(self, image: ImageRef) -> None:
        dest = f"{self.image_base(image)}:{image.version}"
        src = f"docker://docker.io/{image.source}"

        try:
            # Fast path
            self._run_copy(src=src, dest=dest)

        except subprocess.CalledProcessError as e:
            # Always print skopeo output for debugging
            output = (e.stdout or "") + (e.stderr or "")
            if output.strip():
                print(output, flush=True)

            # Fallback: force recompress (avoids cross-repo blob reuse)
            if self._looks_like_blob_reuse_problem(e):
                self._run_copy(
                    src=src,
                    dest=dest,
                    extra=[
                        "--dest-compress-format",
                        "gzip",
                        "--dest-compress-level",
                        "1",
                        "--dest-force-compress-format",
                    ],
                )
                self.ensure_public(image)
                return

            raise

        self.ensure_public(image)


class GiteaProvider(RegistryProvider):
    def __init__(self, registry: str, namespace: str, prefix: str = "mirror") -> None:
        self.registry = registry.rstrip("/")
        self.namespace = namespace
        self.prefix = prefix.strip("/")

    def image_base(self, image: ImageRef) -> str:
        mapped = image.name.replace("/", "-")
        return f"{self.registry}/{self.namespace}/{self.prefix}/{mapped}"

    def tag_exists(self, image: ImageRef) -> bool:
        """
        Return True if the destination tag already exists in the target registry.

        Uses: skopeo inspect docker://<dest>
        Exit code:
          - 0 => exists
          - !=0 => does not exist OR cannot be accessed (auth/network)
        """
        dest = f"{self.image_base(image)}:{image.version}"
        r = subprocess.run(
            ["skopeo", "inspect", f"docker://{dest}"],
            check=False,
            capture_output=True,
            text=True,
        )
        return r.returncode == 0

    def mirror(self, image: ImageRef) -> None:
        dest = f"{self.image_base(image)}:{image.version}"
        src = f"docker://docker.io/{image.source}"

        cmd = [
            "skopeo",
            "copy",
            "--all",
            "--retry-times",
            "5",
            "--dest-precompute-digests",
            src,
            f"docker://{dest}",
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            output = (e.stdout or "") + (e.stderr or "")
            if output.strip():
                print(output, flush=True)
            raise
