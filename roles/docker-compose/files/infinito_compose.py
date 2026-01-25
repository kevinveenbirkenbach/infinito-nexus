#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional


def detect_env_file(project_dir: Path) -> Optional[Path]:
    """
    Detect Compose env file in a directory.
    Preference:
      1) <dir>/.env (file)
      2) <dir>/.env/env (file)  (legacy layout)
    """
    c1 = project_dir / ".env"
    if c1.is_file():
        return c1
    c2 = project_dir / ".env" / "env"
    if c2.is_file():
        return c2
    return None


def detect_compose_files(project_dir: Path) -> List[Path]:
    """
    Detect Compose file stack in a directory.
    Always requires docker-compose.yml.
    Optionals:
      - docker-compose.override.yml
      - docker-compose.ca.override.yml
    """
    base = project_dir / "docker-compose.yml"
    if not base.is_file():
        raise FileNotFoundError(f"Missing docker-compose.yml in: {project_dir}")

    files = [base]

    override = project_dir / "docker-compose.override.yml"
    if override.is_file():
        files.append(override)

    ca_override = project_dir / "docker-compose.ca.override.yml"
    if ca_override.is_file():
        files.append(ca_override)

    return files


def build_cmd(project: str, project_dir: Path, passthrough: List[str]) -> List[str]:
    files = detect_compose_files(project_dir)
    env_file = detect_env_file(project_dir)

    cmd: List[str] = ["docker", "compose", "-p", project]
    for f in files:
        cmd += ["-f", str(f)]
    if env_file:
        cmd += ["--env-file", str(env_file)]

    cmd += passthrough
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Infinito.Nexus docker compose wrapper (auto env + overrides)"
    )
    ap.add_argument("--chdir", required=True, help="Compose project directory")
    ap.add_argument("--project", required=True, help="Compose project name (-p)")
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Print resolved command to stderr before execution",
    )
    ap.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to `docker compose` (e.g. up -d, restart, down -v, ps -a)",
    )
    args = ap.parse_args()

    project_dir = Path(args.chdir)
    if not project_dir.is_dir():
        print(
            f"[infinito-compose] --chdir is not a directory: {project_dir}",
            file=sys.stderr,
        )
        return 2

    passthrough = args.args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]
    if not passthrough:
        print("[infinito-compose] No docker compose args provided.", file=sys.stderr)
        return 2

    try:
        cmd = build_cmd(args.project, project_dir, passthrough)
    except Exception as exc:
        print(f"[infinito-compose] {exc}", file=sys.stderr)
        return 2

    if args.debug:
        print(">>> " + " ".join(cmd), file=sys.stderr)

    # execvp keeps signals behavior nice (systemd etc.)
    os.execvp(cmd[0], cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
