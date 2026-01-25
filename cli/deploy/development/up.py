from __future__ import annotations

import argparse
import os

from .build import handler as build_handler
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
        "--skip-entry-init",
        action="store_true",
        help="Do not run /opt/src/infinito/scripts/docker/entry.sh true after stack is up.",
    )
    p.add_argument(
        "--when-down",
        action="store_true",
        help="Only start stack if it is not already running.",
    )
    p.set_defaults(_handler=handler)


def _maybe_build_missing(*, distro: str) -> int:
    # CI: never build (image is pulled). Local: build if missing.
    if os.environ.get("INFINITO_NO_BUILD", "0") == "1":
        return 0

    build_args = argparse.Namespace(
        distro=distro,
        missing=True,
        no_cache=False,
        target="",
        tag="",
        push=False,
        publish=False,
        registry="",
        owner="",
        repo_prefix="",
        version="",
        stable="",
    )

    return int(build_handler(build_args))


def _stack_is_running(*, distro: str) -> bool:
    compose = make_compose(distro=distro)
    r = compose.run(["ps", "-q", "infinito"], check=False, capture=True)
    cid = (r.stdout or "").strip()
    return bool(cid)


def handler(args: argparse.Namespace) -> int:
    # when-down: skip if already running
    if args.when_down:
        if _stack_is_running(distro=args.distro):
            print(">>> Stack already running — skipping up")
            return 0

    rc = _maybe_build_missing(distro=args.distro)
    if rc != 0:
        return rc

    compose = make_compose(distro=args.distro)
    compose.up(run_entry_init=not bool(args.skip_entry_init))
    return 0
