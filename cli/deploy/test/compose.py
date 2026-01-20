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

    def _render_coredns_corefile(self):
        env = os.environ.copy()

        # load env.ci into environment
        with open("env.ci") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env[k] = v

        subprocess.check_call(
            ["envsubst"],
            stdin=open("compose/Corefile.tmpl"),
            stdout=open("compose/Corefile", "w"),
            env=env,
        )

    def build_infinito(self, *, no_cache: bool, missing_only: bool) -> None:
        if os.environ.get("INFINITO_NO_BUILD", "0") == "1":
            print(">>> INFINITO_NO_BUILD=1 -> skipping docker compose build")
            return

        # image name in compose: "infinito-${INFINITO_DISTRO}"
        image = os.environ.get("INFINITO_IMAGE") or f"infinito-{self.distro}"

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
        print(">>> Rendering CoreDNS Corefile from template")
        self._render_coredns_corefile()

        print(">>> Starting compose stack (coredns + infinito)")
        env = self._base_env()
        keys = [
            "INFINITO_DISTRO",
            "INFINITO_IMAGE",
            "INFINITO_IMAGE_TAG",
            "INFINITO_PULL_POLICY",
            "INFINITO_NO_BUILD",
            "GITHUB_SHA",
        ]
        print(">>> env:", {k: env.get(k) for k in keys})
        print(">>> NIX_CONFIG:", "<set>" if env.get("NIX_CONFIG") else "<empty>")

        no_build = os.environ.get("INFINITO_NO_BUILD", "0") == "1"
        args = ["--env-file", "env.ci", "up", "-d"]
        if no_build:
            args.append("--no-build")
        args += ["coredns", "infinito"]

        self.run(args, check=True)
        self.wait_for_healthy()

        if run_init:
            print(">>> Running infinito entry.sh init")
            r = self.exec(
                ["sh", "-lc", "/opt/src/infinito/scripts/docker/entry.sh true"],
                workdir="/opt/src/infinito",
                check=False,
                capture=True,
            )

            if r.returncode != 0:
                print("===== entry.sh stdout =====")
                print(r.stdout or "<empty>")
                print("===== entry.sh stderr =====")
                print(r.stderr or "<empty>")
                raise RuntimeError(f"entry.sh init failed (rc={r.returncode})")

    def down(self) -> None:
        from .down import down_stack

        down_stack(repo_root=self.repo_root, distro=self.distro)

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

    def _get_infinito_container_id(self) -> str:
        """
        Resolve infinito container ID via docker compose.
        Works independent of project name.
        """
        r = self.run(["ps", "-q", "infinito"], capture=True, check=True)
        cid = r.stdout.strip()

        if not cid:
            raise RuntimeError(
                "infinito container not found (docker compose ps -q infinito returned empty)"
            )

        return cid

    def wait_for_healthy(self, *, timeout_s: int = 200) -> None:
        """
        Wait until infinito container is marked healthy by Docker.
        On timeout: print last 200 log lines for debugging.
        """
        print(">>> Waiting for infinito container to become healthy")

        cid = self._get_infinito_container_id()
        start = time.time()

        while True:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Health.Status}}", cid],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            status = r.stdout.strip() if r.returncode == 0 else ""

            if status == "healthy":
                print(">>> infinito container is healthy")
                return

            if status == "unhealthy":
                print(">>> infinito container is unhealthy")

            if (time.time() - start) > timeout_s:
                print(
                    ">>> ERROR: infinito container not healthy, dumping last 200 log lines\n"
                )

                # Preferred: systemd logs
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
                    ["docker", "logs", "--tail", "200", cid],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                )

                print("===== docker logs (last 200 lines) =====")
                print(docker_logs.stdout or "<no output>")
                print("=======================================\n")

                raise RuntimeError(
                    f"infinito container not healthy after {timeout_s}s "
                    f"(last status: {status})"
                )

            time.sleep(2)
