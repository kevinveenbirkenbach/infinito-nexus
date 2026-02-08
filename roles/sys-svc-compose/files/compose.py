#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
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
    Always requires compose.yml.
    Optionals:
      - compose.override.yml
      - compose.ca.override.yml
    """
    base = project_dir / "compose.yml"
    if not base.is_file():
        raise FileNotFoundError(f"Missing compose.yml in: {project_dir}")

    files = [base]

    override = project_dir / "compose.override.yml"
    if override.is_file():
        files.append(override)

    ca_override = project_dir / "compose.ca.override.yml"
    if ca_override.is_file():
        files.append(ca_override)

    return files


def resolve_files(project_dir: Path, files: List[str]) -> List[Path]:
    """
    Resolve -f/--file arguments (absolute or relative to project_dir).
    """
    out: List[Path] = []
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = project_dir / p
        out.append(p.resolve())
    return out


def build_cmd(
    project: str,
    project_dir: Path,
    passthrough: List[str],
    extra_files: Optional[List[str]] = None,
) -> List[str]:
    """
    Build final `docker compose ...` command.

    Behavior:
    - Always auto-detect compose files in project_dir
    - If -f/--file is provided, append those files *after* autodetected ones
    """
    files = detect_compose_files(project_dir)

    if extra_files:
        files.extend(resolve_files(project_dir, extra_files))

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
    ap.add_argument(
        "--chdir",
        help="Compose project directory (default: current working directory)",
    )
    ap.add_argument(
        "-f",
        "--file",
        action="append",
        dest="files",
        help="Additional compose file(s) appended after auto-detected files",
    )
    ap.add_argument(
        "--project",
        help="Compose project name (-p) (default: basename of chdir)",
    )
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

    project_dir = Path(args.chdir) if args.chdir else Path.cwd()
    project_dir = project_dir.resolve()

    if not project_dir.is_dir():
        print(
            f"[compose] --chdir is not a directory: {project_dir}",
            file=sys.stderr,
        )
        return 2

    project = args.project if args.project else project_dir.name

    passthrough = args.args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]
    if not passthrough:
        print("[compose] No docker compose args provided.", file=sys.stderr)
        return 2

    try:
        cmd = build_cmd(
            project=project,
            project_dir=project_dir,
            passthrough=passthrough,
            extra_files=args.files,
        )
    except Exception as exc:
        print(f"[compose] {exc}", file=sys.stderr)
        return 2

    if args.debug:
        print(">>> " + " ".join(shlex.quote(x) for x in cmd), file=sys.stderr)

    # execvp keeps signals behavior nice (systemd etc.)
    os.execvp(cmd[0], cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
