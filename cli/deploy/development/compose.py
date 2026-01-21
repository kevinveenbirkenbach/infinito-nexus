from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .coredns import CoreDNSCorefileRenderer
from .proc import run_streaming


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

    def _is_ci(self) -> bool:
        # keep this conservative (CI -> no TTY by default)
        return (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("RUNNING_ON_GITHUB") == "true"
            or os.environ.get("CI") == "true"
        )

    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        capture: bool = False,
        live: bool = False,
        keep_lines: int = 400,
        text: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        cmd = ["docker", "compose", "--profile", "ci", *args]
        env = self._base_env()
        if extra_env:
            env.update({k: str(v) for k, v in extra_env.items()})

        if live:
            r = run_streaming(
                cmd, cwd=self.repo_root, env=env, keep_lines=keep_lines, text=text
            )
        else:
            r = subprocess.run(
                cmd,
                cwd=self.repo_root,
                env=env,
                check=False,  # handle check ourselves for consistent behavior
                capture_output=capture,
                text=text,
            )

        if check and int(r.returncode) != 0:
            raise subprocess.CalledProcessError(
                int(r.returncode), cmd, output=r.stdout, stderr=r.stderr
            )

        return r

    def _render_coredns_corefile(self) -> None:
        renderer = CoreDNSCorefileRenderer(repo_root=self.repo_root)
        out = renderer.render(show_preview=True, preview_lines=25)
        print(f"[compose] Corefile generated at: {out}")
        print(
            f"[compose] Corefile exists={out.exists()} "
            f"size={out.stat().st_size if out.exists() else 'n/a'}"
        )

    def up(self, *, run_entry_init: bool = True) -> None:
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

        # IMPORTANT: use the same env snapshot that docker compose will use
        no_build = env.get("INFINITO_NO_BUILD", "0") == "1"

        args = ["--env-file", "env.ci", "up", "-d"]
        if no_build:
            args.append("--no-build")
        args += ["coredns", "infinito"]

        self.run(args, check=True)
        self.wait_for_healthy()

        if run_entry_init:
            print(">>> Running infinito entry.sh init")
            r = self.exec(
                ["sh", "-lc", "/opt/src/infinito/scripts/docker/entry.sh true"],
                workdir="/opt/src/infinito",
                check=False,
                live=True,  # <--- live output
                keep_lines=400,  # <--- tail for failure printing
                extra_env={
                    "ANSIBLE_FORCE_COLOR": "1",
                    "PY_COLORS": "1",
                    "TERM": "xterm-256color",
                },
            )

            if r.returncode != 0:
                print("===== entry.sh stdout (tail) =====")
                print((r.stdout or "").rstrip() or "<empty>")
                print("===== entry.sh stderr (tail) =====")
                print((r.stderr or "").rstrip() or "<empty>")
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
        live: bool = False,
        keep_lines: int = 400,
        tty: bool | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Execute inside infinito container.

        TTY behavior:
          - tty=None  -> auto (local: True, CI: False)
          - tty=True  -> allocate TTY (colors, interactive)
          - tty=False -> -T (CI safe)

        Streaming:
          - live=True streams stdout/stderr to terminal while keeping a tail buffer.
        """
        if tty is None:
            tty = not self._is_ci()

        args = ["exec"]
        if not tty:
            args.append("-T")

        if workdir:
            args += ["-w", workdir]

        if extra_env:
            for k, v in extra_env.items():
                args += ["-e", f"{k}={v}"]

        args += ["infinito", *cmd]

        return self.run(
            args,
            check=check,
            capture=capture,
            live=live,
            keep_lines=keep_lines,
        )

    def _get_infinito_container_id(self) -> str:
        """
        Resolve infinito container ID via docker compose.
        Works independent of project name.
        """
        r = self.run(["ps", "-q", "infinito"], capture=True, check=True)
        cid = (r.stdout or "").strip()

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
                check=False,
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

                logs = self.exec(
                    ["sh", "-lc", "journalctl -n 200 --no-pager || true"],
                    check=False,
                    capture=True,
                )

                print("===== journalctl (last 200 lines) =====")
                print(logs.stdout or "<no output>")
                print("======================================\n")

                docker_logs = subprocess.run(
                    ["docker", "logs", "--tail", "200", cid],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                print("===== docker logs (last 200 lines) =====")
                print(docker_logs.stdout or "<no output>")
                print("=======================================\n")

                raise RuntimeError(
                    f"infinito container not healthy after {timeout_s}s "
                    f"(last status: {status})"
                )

            time.sleep(2)
