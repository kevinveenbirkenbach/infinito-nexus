from __future__ import annotations

import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

from cli.core.colors import Fore, Style, color_text
from cli.core.discovery import resolve_command_module
from cli.core.git import git_clean_repo
from cli.core.help import (
    print_global_help,
    show_full_help_for_all,
    show_help_for_directory,
)
from cli.core.run import RunConfig, open_log_file, run_command_once
from cli.core.sounds import init_multiprocessing, play_start_intro_async


@dataclass
class Flags:
    sound_enabled: bool = False
    no_signal: bool = False
    log_enabled: bool = False
    git_clean: bool = False
    infinite: bool = False
    help_all: bool = False
    alarm_timeout: int = 60


def _first_non_flag_token(argv: List[str]) -> str | None:
    for token in argv[1:]:  # skip argv[0] (program name)
        if token.startswith("-"):
            continue
        return token
    return None


def parse_flags(argv: List[str]) -> Flags:
    flags = Flags()

    flags.sound_enabled = "--sound" in argv and (argv.remove("--sound") or True)
    flags.no_signal = "--no-signal" in argv and (argv.remove("--no-signal") or True)

    flags.log_enabled = "--log" in argv
    if flags.log_enabled:
        first_cmd = _first_non_flag_token(argv)
        if first_cmd != "deploy":
            argv.remove("--log")
            flags.log_enabled = False

    flags.git_clean = "--git-clean" in argv and (argv.remove("--git-clean") or True)
    flags.infinite = "--infinite" in argv and (argv.remove("--infinite") or True)
    flags.help_all = "--help-all" in argv and (argv.remove("--help-all") or True)

    if "--alarm-timeout" in argv:
        i = argv.index("--alarm-timeout")
        try:
            flags.alarm_timeout = int(argv[i + 1])
            del argv[i : i + 2]
        except Exception:
            print(color_text("Invalid --alarm-timeout value!", Fore.RED))
            raise SystemExit(1)

    return flags


def main() -> None:
    init_multiprocessing()

    argv = sys.argv[:]  # keep sys.argv for external tools, but parse on a copy
    flags = parse_flags(argv)
    args = argv[1:]

    # Play intro melody if requested
    if flags.sound_enabled:
        threading.Thread(target=play_start_intro_async, daemon=True).start()

    cli_dir = Path(__file__).resolve().parents[1]  # .../cli/core/app.py -> .../cli
    # sanity: cli_dir should contain __init__.py and __main__.py of dispatcher
    # but we do not hard-fail here

    if flags.git_clean:
        git_clean_repo()

    # Global "show help for all commands" mode
    if flags.help_all:
        print_global_help(cli_dir)
        print(color_text("Full detailed help for all subcommands:", Style.BRIGHT))
        print()
        show_full_help_for_all(cli_dir)
        raise SystemExit(0)

    # Global help
    if not args or args[0] in ("-h", "--help"):
        print_global_help(cli_dir)
        raise SystemExit(0)

    # Directory-specific help: "<path> -h"
    if len(args) > 1 and args[-1] in ("-h", "--help"):
        dir_parts = args[:-1]
        if show_help_for_directory(cli_dir, dir_parts):
            raise SystemExit(0)

    # Resolve command module by package folders with __main__.py
    module, remaining = resolve_command_module(cli_dir, args)
    if not module:
        print(color_text(f"Error: command '{' '.join(args)}' not found.", Fore.RED))
        raise SystemExit(1)

    # If user requested help for the resolved command, forward directly
    if remaining and remaining[0] in ("-h", "--help"):
        subprocess.run([sys.executable, "-m", module, remaining[0]])
        raise SystemExit(0)

    log_file = None
    if flags.log_enabled:
        log_file, log_path = open_log_file()
        print(color_text(f"Tip: Log file created at {log_path}", Fore.GREEN))

    full_cmd = [sys.executable, "-m", module] + remaining

    cfg = RunConfig(
        no_signal=flags.no_signal,
        sound_enabled=flags.sound_enabled,
        alarm_timeout=flags.alarm_timeout,
        log_enabled=flags.log_enabled,
    )

    try:
        if flags.infinite:
            print(color_text("Starting infinite execution mode...", Fore.CYAN))
            count = 1
            while True:
                print(color_text(f"Run #{count}", Style.BRIGHT))
                run_command_once(full_cmd, cfg, log_file)
                count += 1
        else:
            run_command_once(full_cmd, cfg, log_file)
            raise SystemExit(0)
    except KeyboardInterrupt:
        print()
        print(color_text("Execution interrupted by user (Ctrl+C).", Fore.YELLOW))
        raise SystemExit(130)
    finally:
        if log_file:
            log_file.close()
