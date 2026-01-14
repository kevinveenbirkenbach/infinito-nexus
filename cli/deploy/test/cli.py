from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from .runner import run_test_plan


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cli.deploy.test",
        description="CI deploy test orchestrator (compose-based).",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["server", "workstation", "universal"],
        help="Deploy type.",
    )
    parser.add_argument(
        "--distro",
        default=os.environ.get("INFINITO_DISTRO", "arch"),
        choices=["arch", "debian", "ubuntu", "fedora", "centos"],
        help="Target distro (also used for compose image tag).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Rebuild compose image with --no-cache.",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="Build only if missing (skip build if image exists).",
    )
    parser.add_argument(
        "--app",
        default=None,
        help="Run server deploy test only for this single application_id (plus run_after deps).",
    )
    parser.add_argument(
        "--logs-dir",
        default="logs",
        help="Directory for log files (default: logs).",
    )
    parser.add_argument(
        "--keep-stack-on-failure",
        action="store_true",
        help="Do not tear down compose stack on failure.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable/disable Ansible debug mode for the deploy run (default: disabled).",
    )

    args = parser.parse_args(argv)

    # Ensure env is consistent with compose usage
    os.environ["INFINITO_DISTRO"] = args.distro

    logs_dir = Path(args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    return run_test_plan(
        deploy_type=args.type,
        distro=args.distro,
        no_cache=args.no_cache,
        missing_only=args.missing,
        only_app=args.app,
        logs_dir=logs_dir,
        keep_stack_on_failure=args.keep_stack_on_failure,
        debug=args.debug,
    )
