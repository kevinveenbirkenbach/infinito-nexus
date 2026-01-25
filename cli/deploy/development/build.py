from __future__ import annotations

import argparse
import os
import subprocess

from .common import repo_root_from_here


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "build", help="Build infinito image using scripts/build/image.sh (SPOT)."
    )
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (INFINITO_DISTRO).",
    )
    p.add_argument("--missing", action="store_true", help="Build only if missing.")
    p.add_argument("--no-cache", action="store_true", help="Build with --no-cache.")
    p.add_argument("--target", help="Dockerfile target (e.g. virgin).", default="")
    p.add_argument("--tag", help="Override output tag.", default="")
    p.add_argument("--push", action="store_true", help="Push image (buildx).")
    p.add_argument(
        "--publish", action="store_true", help="Publish semantic tags (implies --push)."
    )
    p.add_argument("--registry", default="", help="Registry (e.g. ghcr.io).")
    p.add_argument("--owner", default="", help="Owner/namespace (e.g. org/user).")
    p.add_argument("--repo-prefix", default="", help="Repo prefix (default: infinito).")
    p.add_argument("--version", default="", help="Version (required for --publish).")
    p.add_argument(
        "--stable", choices=["true", "false"], default="", help="Publish stable tags."
    )

    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    repo_root = repo_root_from_here()
    script = repo_root / "scripts" / "build" / "image.sh"

    env = dict(os.environ)
    env["INFINITO_DISTRO"] = args.distro

    cmd: list[str] = [str(script)]
    if args.missing:
        cmd.append("--missing")
    if args.no_cache:
        cmd.append("--no-cache")
    if args.target:
        cmd += ["--target", args.target]
    if args.tag:
        cmd += ["--tag", args.tag]
    if args.push:
        cmd.append("--push")
    if args.publish:
        cmd.append("--publish")
    if args.registry:
        cmd += ["--registry", args.registry]
    if args.owner:
        cmd += ["--owner", args.owner]
    if args.repo_prefix:
        cmd += ["--repo-prefix", args.repo_prefix]
    if args.version:
        cmd += ["--version", args.version]
    if args.stable:
        cmd += ["--stable", args.stable]

    r = subprocess.run(cmd, cwd=repo_root, env=env, check=False)
    return int(r.returncode)
