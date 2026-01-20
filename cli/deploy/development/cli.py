from __future__ import annotations

import argparse
from typing import Optional

from . import deploy as cmd_deploy
from . import down as cmd_down
from . import exec as cmd_exec
from . import init as cmd_init
from . import logs as cmd_logs
from . import restart as cmd_restart
from . import run as cmd_run
from . import stop as cmd_stop
from . import up as cmd_up


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cli.deploy.development",
        description="Compose-based development deploy orchestrator for Infinito.Nexus.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    cmd_up.add_parser(sub)
    cmd_down.add_parser(sub)
    cmd_stop.add_parser(sub)
    cmd_restart.add_parser(sub)
    cmd_init.add_parser(sub)
    cmd_deploy.add_parser(sub)
    cmd_run.add_parser(sub)
    cmd_exec.add_parser(sub)
    cmd_logs.add_parser(sub)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    fn = getattr(args, "_handler", None)
    if fn is None:
        parser.error("No subcommand handler registered")  # pragma: no cover

    return int(fn(args))
