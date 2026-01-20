from __future__ import annotations

import argparse
import os
from pathlib import Path

from .common import make_compose, resolve_deploy_ids_for_app
from .init import handler as init_handler
from .deploy import handler as deploy_handler
from .log_utils import append_text, log_path, write_text


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
        "--no-cache", action="store_true", help="Rebuild compose image with --no-cache."
    )
    p.add_argument("--missing", action="store_true", help="Build only if missing.")
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
    compose = make_compose(distro=args.distro)

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

    try:
        compose.build_infinito(
            no_cache=bool(args.no_cache), missing_only=bool(args.missing)
        )
        compose.up(run_entry_init=not bool(args.skip_entry_init))

        deploy_ids = resolve_deploy_ids_for_app(compose, args.app)
        append_text(main_log, f"\nresolved_ids={','.join(deploy_ids)}\n")

        # init subcommand (re-using its handler via a tiny args object)
        class _InitArgs:
            distro = args.distro
            app = args.app
            include = None
            threshold_gib = 100
            force_storage_constrained = None

        init_handler(_InitArgs())

        # deploy subcommand
        class _DeployArgs:
            distro = args.distro
            type = args.type
            app = args.app
            id = None
            debug = args.debug
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
        if not should_keep:
            try:
                compose.down()
            except Exception:
                pass
