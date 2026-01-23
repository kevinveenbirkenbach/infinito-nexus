#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> int:
    p = subprocess.run(cmd, cwd=str(cwd), env=env)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run docker compose with common Infinito.Nexus conventions"
    )
    ap.add_argument("--chdir", required=True, help="Compose instance directory")
    ap.add_argument("--project", required=True, help="Compose project name (-p)")
    ap.add_argument(
        "--compose-files",
        required=True,
        help='Compose files args string like: "-f a.yml -f b.yml"',
    )
    ap.add_argument("--env-file", default="", help="Optional env file path")
    ap.add_argument("--debug", action="store_true", help="Enable debug output")
    ap.add_argument(
        "--print-env-unmasked",
        action="store_true",
        help="Print .env unmasked (debug only)",
    )
    ap.add_argument("--action", choices=["config", "up"], required=True)
    ap.add_argument(
        "--up-flags", default="--force-recreate --remove-orphans", help="Flags for `up`"
    )
    ap.add_argument("--detach", action="store_true", help="Add -d to `up`")
    args = ap.parse_args()

    cwd = Path(args.chdir)
    env = dict(os.environ)

    base = ["docker", "compose", "-p", args.project]
    # compose-files is a string; split safely on whitespace (we control generation)
    base += args.compose_files.split()

    env_file = args.env_file.strip()
    if env_file:
        base += ["--env-file", env_file]

    if args.debug:
        print(">>> [dc][DEBUG] docker compose config (FULL)", file=sys.stderr)
        rc = run(base + ["config"], cwd=cwd, env=env)
        if rc != 0:
            return rc

        if args.print_env_unmasked and env_file and Path(env_file).exists():
            print(">>> [dc][DEBUG] .env (UNMASKED)", file=sys.stderr)
            try:
                print(
                    Path(env_file).read_text(encoding="utf-8"), file=sys.stderr, end=""
                )
            except Exception:
                # best effort; don't fail the deployment
                pass

    if args.action == "config":
        return run(base + ["config"], cwd=cwd, env=env)

    # action == up
    up_cmd = base + ["up"]
    if args.detach:
        up_cmd.append("-d")
    if args.up_flags.strip():
        up_cmd += args.up_flags.split()

    return run(up_cmd, cwd=cwd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
