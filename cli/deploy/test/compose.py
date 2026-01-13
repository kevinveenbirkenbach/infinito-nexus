from __future__ import annotations

import os
import subprocess
import time
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

    def up(self, *, run_init: bool = True) -> None:
        print(">>> Starting compose stack (coredns + infinito)")

        no_build = os.environ.get("INFINITO_NO_BUILD", "0") == "1"
        args = ["up", "-d"]
        if no_build:
            args.append("--no-build")
        args += ["coredns", "infinito"]

        self.run(args, check=True)

        print(">>> Waiting for systemd to be ready")
        self.wait_for_systemd_ready()

        if run_init:
            print(">>> Running infinito entry.sh init")
            self.exec(
                ["sh", "-lc", "/opt/src/infinito/scripts/docker/entry.sh true"],
                workdir="/opt/src/infinito",
            )

    def down(self) -> None:
        print(">>> Stopping compose stack and removing volumes")
        self.run(["down", "--remove-orphans", "-v"], check=True)

    def exec(
        self,
        cmd: list[str],
        *,
        check: bool = True,
        workdir: str | None = None,
        capture: bool = False,
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
        return self.run(args, check=check, capture=capture)

    def wait_for_systemd_ready(self, *, timeout_s: int = 90) -> None:
        """
        Wait until systemd is ready to accept systemctl calls (DBus + /run/systemd/private).
        Avoids a race right after compose up.
        On timeout: print last 200 log lines for debugging.
        """
        start = time.time()

        while True:
            r = self.exec(
                [
                    "sh",
                    "-lc",
                    # Must have systemd private socket + a stable running/degraded state
                    "test -S /run/systemd/private && "
                    "systemctl is-system-running --wait 2>/dev/null | grep -Eq 'running|degraded'",
                ],
                check=False,
                capture=True,
            )

            if r.returncode == 0:
                return

            if (time.time() - start) > timeout_s:
                print(">>> ERROR: systemd not ready, dumping last 200 log lines\n")

                # Try journalctl first (preferred for systemd containers)
                logs = self.exec(
                    ["sh", "-lc", "journalctl -n 200 --no-pager || true"],
                    check=False,
                    capture=True,
                )

                print("===== journalctl (last 200 lines) =====")
                print(logs.stdout or "<no output>")
                print("======================================\n")

                # Fallback: docker logs
                docker_logs = subprocess.run(
                    ["docker", "logs", "--tail", "200", "infinito"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                )

                print("===== docker logs (last 200 lines) =====")
                print(docker_logs.stdout or "<no output>")
                print("=======================================\n")

                raise RuntimeError(
                    "systemd not ready after waiting.\n"
                    f"last rc={r.returncode}\n"
                    f"STDOUT:\n{r.stdout}\n"
                    f"STDERR:\n{r.stderr}\n"
                )

            time.sleep(1)
