from __future__ import annotations

import argparse
import os

from .common import make_compose


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "stop",
        help="Stop services in the compose stack (no volume removal).",
    )
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)
    r = compose.run(["stop"], check=False)
    return int(r.returncode)
