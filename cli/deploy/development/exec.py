from __future__ import annotations

import argparse
import os

from .common import make_compose


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("exec", help="Execute a command inside the infinito container.")
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )
    p.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command to execute (use `--` to separate).",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)

    cmd = list(args.cmd or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        raise SystemExit("exec requires a command (e.g. exec -- sh -lc 'whoami')")

    r = compose.exec(cmd, check=False)
    return int(r.returncode)
