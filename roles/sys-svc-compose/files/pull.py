#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path


TRANSIENT_RE = re.compile(
    r"("
    r"TLS handshake timeout|i/o timeout|timed out|timeout|"
    r"connection reset|connection refused|temporary failure|try again|"
    r"unexpected EOF|\bEOF\b|recv failure|"
    r"error pulling image configuration|"
    r"image config verification failed|"
    r"could not resolve host|failed to connect|"
    r"network is unreachable|no route to host|"
    r"context deadline exceeded|"
    r"\b502\b|\b503\b|\b504\b|\b429\b|toomanyrequests"
    r")",
    re.IGNORECASE,
)


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return p.returncode, p.stdout or ""


def retry(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    attempts: int,
    sleep_s: float,
    sleep_cap_s: float,
) -> None:
    print(f">>> {' '.join(cmd)}", file=sys.stderr)
    delay = sleep_s
    for attempt in range(1, attempts + 1):
        rc, out = run_cmd(cmd, cwd=cwd, env=env)
        if rc == 0:
            if out.strip():
                print(out, end="" if out.endswith("\n") else "\n")
            return

        if out.strip():
            print(out, file=sys.stderr, end="" if out.endswith("\n") else "\n")

        if not TRANSIENT_RE.search(out):
            raise RuntimeError(
                f"Non-transient failure (rc={rc}) running: {' '.join(cmd)}"
            )

        if attempt >= attempts:
            raise RuntimeError(
                f"Transient failure persisted after {attempts} attempts running: {' '.join(cmd)}"
            )

        print(
            f"Retrying in {delay:.1f}s (next attempt {attempt + 1}/{attempts})...",
            file=sys.stderr,
        )
        time.sleep(delay)
        delay = min(delay * 2, sleep_cap_s)


def base_compose_cmd(*, project: str, compose_files: str, env_file: str) -> list[str]:
    base = ["docker", "compose", "-p", project]
    base += compose_files.split()
    if env_file.strip():
        base += ["--env-file", env_file.strip()]
    return base


def has_buildable_services(
    *, base_cmd: list[str], cwd: Path, env: dict[str, str]
) -> bool:
    rc, out = run_cmd(base_cmd + ["config"], cwd=cwd, env=env)
    if rc != 0:
        raise RuntimeError(
            "docker compose config failed; cannot detect buildable services"
        )
    return any(
        line.lstrip() != line and line.strip().startswith("build:")
        for line in out.splitlines()
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="docker compose pull/build with retries + lock"
    )
    ap.add_argument("--chdir", required=True, help="Compose instance directory")
    ap.add_argument("--project", required=True, help="Compose project name (-p)")
    ap.add_argument(
        "--compose-files",
        required=True,
        help='Compose files args string like: "-f a.yml -f b.yml"',
    )
    ap.add_argument("--env-file", default="", help="Optional env file path")

    ap.add_argument("--lock-dir", required=True, help="Directory for lock files")
    ap.add_argument(
        "--lock-key", required=True, help="Unique lock key (e.g. sha1 of instance dir)"
    )
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--sleep-cap", type=float, default=60.0)
    ap.add_argument("--compose-http-timeout", default="600")
    ap.add_argument("--docker-client-timeout", default="600")
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="Do not run docker compose build --pull",
    )
    ap.add_argument(
        "--ignore-buildable",
        action="store_true",
        help="Use --ignore-buildable when available",
    )
    args = ap.parse_args()

    cwd = Path(args.chdir)
    lock_dir = Path(args.lock_dir)
    lock_file = lock_dir / f"{args.lock_key}.lock"

    if lock_file.exists():
        return 0

    lock_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["COMPOSE_HTTP_TIMEOUT"] = str(args.compose_http_timeout)
    env["DOCKER_CLIENT_TIMEOUT"] = str(args.docker_client_timeout)

    base_cmd = base_compose_cmd(
        project=args.project, compose_files=args.compose_files, env_file=args.env_file
    )

    # 1) build --pull when buildable services exist (unless skipped)
    if not args.skip_build and has_buildable_services(
        base_cmd=base_cmd, cwd=cwd, env=env
    ):
        retry(
            base_cmd + ["build", "--pull"],
            cwd=cwd,
            env=env,
            attempts=args.attempts,
            sleep_s=args.sleep,
            sleep_cap_s=args.sleep_cap,
        )

    # 2) pull (optionally with --ignore-buildable if supported)
    pull_cmd = base_cmd + ["pull"]
    if args.ignore_buildable:
        rc, help_out = run_cmd(base_cmd + ["pull", "--help"], cwd=cwd, env=env)
        if rc == 0 and "--ignore-buildable" in help_out:
            pull_cmd.append("--ignore-buildable")

    retry(
        pull_cmd,
        cwd=cwd,
        env=env,
        attempts=args.attempts,
        sleep_s=args.sleep,
        sleep_cap_s=args.sleep_cap,
    )

    lock_file.write_text("ok\n", encoding="utf-8")
    print("pulled")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
