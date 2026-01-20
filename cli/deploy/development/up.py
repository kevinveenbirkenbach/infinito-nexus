from __future__ import annotations

import argparse
import os

from .common import make_compose


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("up", help="Start compose stack (coredns + infinito).")
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )
    p.add_argument(
        "--no-cache", action="store_true", help="Rebuild image with --no-cache."
    )
    p.add_argument(
        "--missing",
        action="store_true",
        help="Build only if missing (skip build if image exists).",
    )
    p.add_argument(
        "--no-build",
        action="store_true",
        help="Do not build (regardless of INFINITO_NO_BUILD).",
    )
    p.add_argument(
        "--skip-entry-init",
        action="store_true",
        help="Do not run /opt/src/infinito/scripts/docker/entry.sh true after stack is up.",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)

    # Allow explicit no-build via CLI even if local defaults build.
    if args.no_build:
        os.environ["INFINITO_NO_BUILD"] = "1"

    compose.build_infinito(
        no_cache=bool(args.no_cache), missing_only=bool(args.missing)
    )
    compose.up(run_entry_init=not bool(args.skip_entry_init))
    return 0
