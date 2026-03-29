from __future__ import annotations

import argparse
import os

from .common import make_compose, resolve_deploy_ids_for_apps


def _run_deploy(
    compose,
    *,
    deploy_ids: list[str],
    debug: bool,
    passthrough: list[str],
    inventory_dir: str,
) -> int:
    inv_root = str(inventory_dir).rstrip("/")
    inv_file = f"{inv_root}/devices.yml"
    pw_file = f"{inv_root}/.password"

    cmd = [
        "python3",
        "-m",
        "cli.deploy.dedicated",
        inv_file,
        "-p",
        pw_file,
        "-vv",
        "--assert",
        "true",
        "--diff",
        "--id",
        *deploy_ids,
    ]
    if debug:
        cmd.insert(cmd.index("--diff") + 1, "--debug")

    if passthrough:
        cmd.extend(passthrough)

    # Live stream output for immediate visibility.
    r = compose.exec(
        cmd,
        check=False,
        live=True,
        extra_env={
            # Force ANSI colors even when no TTY is allocated (CI default).
            "ANSIBLE_FORCE_COLOR": "1",
            "PY_COLORS": "1",
            "TERM": "xterm-256color",
        },
    )

    return int(r.returncode)


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "deploy", help="Run deploy inside the infinito container (requires inventory)."
    )
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )

    p.add_argument(
        "--inventory-dir",
        default=os.environ.get("INVENTORY_DIR"),
        required=os.environ.get("INVENTORY_DIR") is None,
        help="Inventory directory to use (default: $INVENTORY_DIR).",
    )

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--apps",
        help="One or more application ids (will include run_after deps automatically).",
    )
    g.add_argument(
        "--id",
        nargs="+",
        default=None,
        help="Explicit application ids (space-separated).",
    )
    p.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable/disable Ansible debug mode (default: disabled).",
    )
    p.add_argument(
        "ansible_args",
        nargs=argparse.REMAINDER,
        help="Passthrough args appended to `cli.deploy.dedicated` (use `--` to separate).",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)

    if args.apps:
        deploy_ids = resolve_deploy_ids_for_apps(compose, args.apps)
    else:
        deploy_ids = list(args.id or [])

    # argparse.REMAINDER includes the leading '--' if present; drop it
    passthrough = list(args.ansible_args or [])
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    rc = _run_deploy(
        compose,
        deploy_ids=deploy_ids,
        debug=bool(args.debug),
        passthrough=passthrough,
        inventory_dir=str(args.inventory_dir),
    )
    return rc
