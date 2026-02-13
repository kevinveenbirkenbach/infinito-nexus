# cli/deploy/development/init.py
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

from .common import make_compose, resolve_deploy_ids_for_app
from .mirrors import generate_ci_mirrors_file, should_use_mirrors_on_ci
from .storage import detect_storage_constrained
from ...meta.runtime import detect_runtime


def _ensure_vault_password_file(compose, *, inventory_dir: str) -> None:
    inv_root = str(inventory_dir).rstrip("/")
    pw_file = f"{inv_root}/.password"

    compose.exec(
        [
            "sh",
            "-lc",
            f"mkdir -p {inv_root} && "
            f"[ -f {pw_file} ] || "
            f"printf '%s\n' 'ci-vault-password' > {pw_file}",
        ],
        check=True,
    )


def _create_inventory(
    compose,
    *,
    include: list[str],
    storage_constrained: bool,
    inventory_dir: str,
    extra_vars: Dict[str, Any] | None,
) -> None:
    if not include:
        raise ValueError("include must not be empty")

    inv_root = str(inventory_dir).rstrip("/")
    runtime = os.environ.get("RUNTIME") or detect_runtime()

    overrides: Dict[str, Any] = {
        "STORAGE_CONSTRAINED": bool(storage_constrained),
        "RUNTIME": runtime,
    }

    # User-provided vars always win
    if extra_vars:
        overrides.update(extra_vars)

    cmd = [
        "python3",
        "-m",
        "cli.create.inventory",
        inv_root,
        "--host",
        "localhost",
        "--ssl-disabled",
        "--vars-file",
        "inventories/dev.yml",
        "--vars",
        json.dumps(overrides),
        "--include",
        ",".join(include),
    ]

    if should_use_mirrors_on_ci():
        mirrors_file = generate_ci_mirrors_file(compose, inventory_dir=inv_root)
        cmd += ["--mirror", mirrors_file]

    compose.exec(cmd, check=True, workdir="/opt/src/infinito")
    _ensure_vault_password_file(compose, inventory_dir=inv_root)


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "init",
        help="Create development inventory inside the infinito container.",
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
        "--app",
        help="Application id (will include run_after deps automatically).",
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
    p.add_argument(
        "--vars",
        default=None,
        help="JSON object merged into inventory variables (overrides win).",
    )
    p.set_defaults(_handler=handler)


def handler(args: argparse.Namespace) -> int:
    compose = make_compose(distro=args.distro)

    if args.app:
        include = resolve_deploy_ids_for_app(compose, args.app)
    else:
        include = [x.strip() for x in (args.include or "").split(",") if x.strip()]

    if not include:
        raise SystemExit("Resolved include list is empty")

    extra_vars: Dict[str, Any] | None = None
    if args.vars is not None:
        try:
            parsed = json.loads(args.vars)
        except Exception as exc:
            raise SystemExit(f"--vars must be valid JSON: {exc}")
        if not isinstance(parsed, dict):
            raise SystemExit("--vars must be a JSON object")
        extra_vars = parsed

    if args.force_storage_constrained is not None:
        storage_constrained = args.force_storage_constrained == "true"
    else:
        storage_constrained = detect_storage_constrained(
            compose, threshold_gib=int(args.threshold_gib)
        )

    _create_inventory(
        compose,
        include=include,
        storage_constrained=storage_constrained,
        inventory_dir=str(args.inventory_dir),
        extra_vars=extra_vars,
    )

    print(
        f">>> Inventory initialized (include={','.join(include)} "
        f"storage_constrained={storage_constrained})"
    )
    return 0
