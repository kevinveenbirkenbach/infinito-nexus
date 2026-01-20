from __future__ import annotations

import argparse
import os
from pathlib import Path

from .deploy import handler as deploy_handler
from .init import handler as init_handler
from .log_utils import append_text, log_path, write_text
from .common import make_compose, resolve_deploy_ids_for_app
from .up import handler as up_handler


def add_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "run", help="Orchestrator: up -> init -> deploy -> down (optional keep)."
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["server", "workstation", "universal"],
        help="Deploy type.",
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
        help="Do not run entry.sh init after compose up.",
    )
    p.add_argument(
        "--app", required=True, help="Run for this single application_id (plus deps)."
    )
    p.add_argument(
        "--logs-dir", default="logs", help="Directory for log files (default: logs)."
    )
    p.add_argument(
        "--keep-stack-on-failure",
        action="store_true",
        help="Do not tear down compose stack on failure.",
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
    logs_dir = Path(args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    main_log = log_path(logs_dir, args.type, args.distro, "orchestrator")
    write_text(
        main_log,
        f"deploy_type={args.type}\ndistro={args.distro}\napp={args.app}\ndebug={args.debug}\n",
    )

    exit_code = 0

    # Drop leading '--' from REMAINDER
    passthrough = list(args.ansible_args or [])
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    compose = None

    try:
        # 1) up (re-use up handler so build-missing stays SPOT)
        class _UpArgs:
            distro = args.distro
            skip_entry_init = bool(args.skip_entry_init)

        rc_up = int(up_handler(_UpArgs()))
        if rc_up != 0:
            return rc_up

        # Create compose AFTER up so we have a fresh instance for the remainder.
        compose = make_compose(distro=args.distro)

        # 2) resolve deps
        deploy_ids = resolve_deploy_ids_for_app(compose, args.app)
        append_text(main_log, f"\nresolved_ids={','.join(deploy_ids)}\n")

        # 3) init subcommand (re-using its handler via a tiny args object)
        class _InitArgs:
            distro = args.distro
            app = args.app
            include = None
            threshold_gib = 100
            force_storage_constrained = None

        init_handler(_InitArgs())

        # 4) deploy subcommand
        class _DeployArgs:
            distro = args.distro
            type = args.type
            app = args.app
            id = None
            debug = bool(args.debug)
            ansible_args = ["--", *passthrough] if passthrough else []

        rc = deploy_handler(_DeployArgs())
        exit_code = int(rc)

        per_app_log = log_path(logs_dir, args.type, args.distro, f"app-{args.app}")
        write_text(
            per_app_log, f"app={args.app}\nids={','.join(deploy_ids)}\nrc={exit_code}\n"
        )

        if exit_code != 0:
            append_text(
                per_app_log,
                "\n--- hint ---\n"
                "Search workflow logs for the failing task output.\n"
                f"Also run: INFINITO_DISTRO={args.distro} docker compose --profile ci logs --tail=200\n",
            )

        return exit_code
    except Exception as exc:
        exit_code = 1
        append_text(main_log, f"\nERROR: {exc}\n")
        return 1
    finally:
        should_keep = bool(args.keep_stack_on_failure) and exit_code != 0
        if not should_keep and compose is not None:
            try:
                compose.down()
            except Exception:
                pass
