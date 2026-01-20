from __future__ import annotations

import argparse
import json
import os

from .common import make_compose, resolve_deploy_ids_for_app
from .storage import detect_storage_constrained


def _ensure_vault_password_file(compose) -> None:
    compose.exec(
        [
            "sh",
            "-lc",
            "mkdir -p /etc/inventories/github-ci && "
            "[ -f /etc/inventories/github-ci/.password ] || "
            "printf '%s\n' 'ci-vault-password' > /etc/inventories/github-ci/.password",
        ],
        check=True,
    )


def _create_inventory(
    compose, *, include: list[str], storage_constrained: bool
) -> None:
    if not include:
        raise ValueError("include must not be empty")

    overrides = {"STORAGE_CONSTRAINED": bool(storage_constrained)}

    cmd = [
        "python3",
        "-m",
        "cli.create.inventory",
        "/etc/inventories/github-ci",
        "--host",
        "localhost",
        "--ssl-disabled",
        "--vars-file",
        "inventory.sample.yml",
        "--vars",
        json.dumps(overrides),
        "--include",
        ",".join(include),
    ]

    compose.exec(cmd, check=True, workdir="/opt/src/infinito")
    _ensure_vault_password_file(compose)


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "init", help="Create development inventory inside the infinito container."
    )
    p.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (compose env INFINITO_DISTRO).",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--app", help="Application id (will include run_after deps automatically)."
    )
    g.add_argument(
        "--include",
        help="Comma-separated list of application ids to include (no deps resolution).",
    )
    p.add_argument(
        "--threshold-gib",
        type=int,
        default=100,
        help="Free-space threshold (GiB) below which STORAGE_CONSTRAINED is enabled (default: 100).",
    )
    p.add_argument(
        "--force-storage-constrained",
        choices=["true", "false"],
        default=None,
        help="Override storage detection explicitly.",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)

    if args.app:
        include = resolve_deploy_ids_for_app(compose, args.app)
    else:
        include = [x.strip() for x in (args.include or "").split(",") if x.strip()]

    if not include:
        raise ValueError("Resolved include list is empty")

    if args.force_storage_constrained is not None:
        storage_constrained = args.force_storage_constrained == "true"
    else:
        storage_constrained = detect_storage_constrained(
            compose, threshold_gib=int(args.threshold_gib)
        )

    _create_inventory(compose, include=include, storage_constrained=storage_constrained)
    print(
        f">>> Inventory initialized (include={','.join(include)} storage_constrained={storage_constrained})"
    )
    return 0
