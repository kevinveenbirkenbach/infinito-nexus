from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional

from .apps import validate_application_ids
from .modes import add_dynamic_mode_args, build_modes_from_args, load_modes_from_yaml
from .paths import (
    CLI_ROOT,
    INVENTORY_VALIDATOR_PATH,
    MODES_FILE,
    PLAYBOOK_PATH,
    REPO_ROOT,
)
from .runner import run_ansible_playbook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deploy the Infinito.Nexus stack using ansible-playbook."
    )

    # Standard arguments
    parser.add_argument("inventory", help="Path to the inventory file.")
    parser.add_argument(
        "-l", "--limit", help="Limit execution to certain hosts or groups."
    )
    parser.add_argument(
        "-T",
        "--host-type",
        choices=["server", "workstation"],
        default="server",
        help="Specify target type: server or workstation.",
    )
    parser.add_argument(
        "-p", "--password-file", help="Vault password file for encrypted variables."
    )
    parser.add_argument(
        "-B", "--skip-build", action="store_true", help="Skip build phase."
    )
    parser.add_argument(
        "-i",
        "--id",
        nargs="+",
        default=[],
        dest="id",
        help="List of application_ids for partial deployment.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (e.g. -vvv).",
    )
    parser.add_argument("--logs", action="store_true", help="Keep logs during cleanup.")
    parser.add_argument("--diff", action="store_true", help="Enable Ansible diff mode.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint for `python -m cli.deploy.dedicated`.

    `argv` is injectable for tests and avoids reliance on global sys.argv.
    """
    parser = build_parser()

    # Dynamic MODE_* parsing
    modes_meta = load_modes_from_yaml(MODES_FILE)
    modes_spec = add_dynamic_mode_args(parser, modes_meta)

    args = parser.parse_args(argv)

    # Validate application IDs
    validate_application_ids(args.inventory, args.id)

    # Build final mode map
    modes: Dict[str, Any] = build_modes_from_args(modes_spec, args)
    modes["MODE_LOGS"] = args.logs
    modes["host_type"] = args.host_type

    run_ansible_playbook(
        repo_root=REPO_ROOT,
        cli_root=CLI_ROOT,
        playbook_path=PLAYBOOK_PATH,
        inventory_validator_path=INVENTORY_VALIDATOR_PATH,
        inventory=args.inventory,
        modes=modes,
        limit=args.limit,
        allowed_applications=args.id,
        password_file=args.password_file,
        verbose=args.verbose,
        skip_build=args.skip_build,
        logs=args.logs,
        diff=args.diff,
    )

    return 0
