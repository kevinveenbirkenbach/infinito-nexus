from __future__ import annotations

import os
import subprocess
from pathlib import Path


class Compose:
    """
    Small wrapper around:
      INFINITO_DISTRO=<distro> docker compose --profile ci ...
    """

    def __init__(self, repo_root: Path, distro: str) -> None:
        self.repo_root = repo_root
        self.distro = distro

    def _base_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["INFINITO_DISTRO"] = self.distro
        return env

    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        capture: bool = False,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        cmd = ["docker", "compose", "--profile", "ci", *args]
        return subprocess.run(
            cmd,
            cwd=self.repo_root,
            env=self._base_env(),
            check=check,
            capture_output=capture,
            text=text,
        )

    def build_infinito(self, *, no_cache: bool, missing_only: bool) -> None:
        # image name in compose: "infinito-${INFINITO_DISTRO}"
        image = f"infinito-{self.distro}"

        if missing_only:
            r = subprocess.run(
                ["docker", "image", "inspect", image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                print(
                    f">>> Image already exists: {image} (skipping build due to --missing)"
                )
                return

        if no_cache:
            print(
                f">>> docker compose build --no-cache infinito (INFINITO_DISTRO={self.distro})"
            )
            self.run(["build", "--no-cache", "infinito"], check=True)
        else:
            print(f">>> docker compose build infinito (INFINITO_DISTRO={self.distro})")
            self.run(["build", "infinito"], check=True)

    def up(self) -> None:
        print(">>> Starting compose stack (coredns + infinito)")
        self.run(["up", "-d", "coredns", "infinito"], check=True)

    def down(self) -> None:
        print(">>> Stopping compose stack and removing volumes")
        self.run(["down", "--remove-orphans", "-v"], check=True)

    def exec(
        self,
        cmd: list[str],
        *,
        check: bool = True,
        workdir: str | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Execute inside infinito container.
        -T: no pseudo-tty (CI safe)
        -w: set working directory
        """
        args = ["exec", "-T"]
        if workdir:
            args += ["-w", workdir]
        args += ["infinito", *cmd]
        return self.run(args, check=check)
