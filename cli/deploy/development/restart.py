from __future__ import annotations

import argparse
import os

from .stop import handler as stop_handler
from .up import handler as up_handler


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "restart",
        help="Restart the compose stack: stop -> up (no force by default).",
    )
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )

    p.add_argument(
        "--skip-entry-init",
        action="store_true",
        help="Do not run entry.sh init after stack is up.",
    )

    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    # 1) stop (best-effort)
    class _StopArgs:
        distro = args.distro

    stop_rc = stop_handler(_StopArgs())
    if stop_rc != 0:
        print(f">>> WARNING: stop returned rc={stop_rc}, continuing with up")

    # 2) up (normal behavior, no force unless flags provided)
    class _UpArgs:
        distro = args.distro
        skip_entry_init = bool(args.skip_entry_init)
        when_down = False  # <-- REQUIRED by up.handler()

    return int(up_handler(_UpArgs()))
