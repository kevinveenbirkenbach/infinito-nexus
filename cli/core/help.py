from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List

from cli.core.colors import Fore, Style, color_text
from cli.core.discovery import discover_commands


def format_command_help(
    name: str, description: str, indent: int = 2, col_width: int = 36, width: int = 80
) -> str:
    prefix = " " * indent + f"{name:<{col_width - indent}}"
    wrapper = textwrap.TextWrapper(
        width=width, initial_indent=prefix, subsequent_indent=" " * col_width
    )
    return wrapper.fill(description)


def extract_description_via_help(module: str) -> str:
    """
    Best-effort: run "python -m <module> --help" and extract the first paragraph after usage.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (result.stdout or "").splitlines()

        # heuristic:
        # skip usage line(s) then return first non-empty line after the first blank line
        seen_usage = False
        for i, line in enumerate(out):
            if line.strip().startswith("usage:"):
                seen_usage = True
                continue
            if not seen_usage:
                continue
            if not line.strip():
                for j in range(i + 1, len(out)):
                    desc = out[j].strip()
                    if desc:
                        return desc
                break
        return "-"
    except Exception:
        return "-"


def print_global_help(cli_dir: Path) -> None:
    commands = discover_commands(cli_dir)

    print(color_text("Infinito.Nexus CLI 🦫🌐🖥️", Fore.CYAN + Style.BRIGHT))
    print()
    print(color_text("Your Gateway to Automated IT Infrastructure Setup", Style.DIM))
    print()
    print(
        color_text(
            "Usage: infinito "
            "[--sound] "
            "[--no-signal] "
            "[--log <LOG_DIR>] "
            "[--git-clean] "
            "[--infinite] "
            "[--help-all] "
            "[--alarm-timeout <seconds>] "
            "[-h|--help] "
            "<command> [options]",
            Fore.GREEN,
        )
    )
    print()
    print(color_text("Options:", Style.BRIGHT))
    print(
        color_text(
            "  --sound           Play startup melody and warning sounds", Fore.YELLOW
        )
    )
    print(
        color_text("  --no-signal       Suppress success/failure signals", Fore.YELLOW)
    )
    print(
        color_text(
            "  --log <LOG_DIR>   Log all proxied command output to <LOG_DIR>/<timestamp>.log",
            Fore.YELLOW,
        )
    )
    print(
        color_text(
            "  --git-clean       Remove all Git-ignored files before running",
            Fore.YELLOW,
        )
    )
    print(
        color_text(
            "  --infinite        Run the proxied command in an infinite loop",
            Fore.YELLOW,
        )
    )
    print(
        color_text(
            "  --help-all        Show full --help for all CLI commands", Fore.YELLOW
        )
    )
    print(
        color_text(
            "  --alarm-timeout   Stop warnings and exit after N seconds (default: 60)",
            Fore.YELLOW,
        )
    )
    print(
        color_text("  -h, --help        Show this help message and exit", Fore.YELLOW)
    )
    print()
    print(color_text("Available commands:", Style.BRIGHT))
    print()

    current_folder: str | None = None
    for cmd in commands:
        if cmd.folder != current_folder:
            if cmd.folder:
                print(color_text(f"{cmd.folder}/", Fore.MAGENTA))
                print()
            current_folder = cmd.folder

        desc = extract_description_via_help(cmd.module)
        print(color_text(format_command_help(cmd.name, desc, indent=2), ""), "\n")

    print()
    print(
        color_text(
            "🔗  You can chain subcommands by specifying nested directories,", Fore.CYAN
        )
    )
    print(color_text("    e.g. infinito build tree", Fore.CYAN))
    print(color_text("    corresponds to cli/build/tree/__main__.py.", Fore.CYAN))
    print()
    print(
        color_text(
            "Infinito.Nexus is a product of Kevin Veen-Birkenbach, https://cybermaster.space .\n",
            Style.DIM,
        )
    )
    print(
        color_text("Test and use productively on https://infinito.nexus .\n", Style.DIM)
    )
    print(
        color_text(
            "For commercial use, a license agreement with Kevin Veen-Birkenbach is required. \n",
            Style.DIM,
        )
    )
    print(color_text("License: https://s.infinito.nexus/license", Style.DIM))
    print()
    print(
        color_text(
            "🎉🌈 Happy IT Infrastructuring! 🚀🔧✨", Fore.MAGENTA + Style.BRIGHT
        )
    )
    print()


def show_full_help_for_all(cli_dir: Path) -> None:
    commands = discover_commands(cli_dir)

    print(
        color_text("Infinito.Nexus CLI – Full Help Overview", Fore.CYAN + Style.BRIGHT)
    )
    print()

    for cmd in commands:
        file_path = str(
            cmd.main_path.relative_to(cli_dir.parent)
        )  # cli/<...>/__main__.py
        print(color_text("=" * 80, Fore.BLUE + Style.BRIGHT))
        print(color_text(f"Subcommand: {cmd.subcommand}", Fore.YELLOW + Style.BRIGHT))
        print(color_text(f"File: {file_path}", Fore.CYAN))
        print(color_text("-" * 80, Fore.BLUE))

        try:
            result = subprocess.run(
                [sys.executable, "-m", cmd.module, "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(color_text(result.stderr.rstrip(), Fore.RED))
        except Exception as e:
            print(color_text(f"Failed to get help for {file_path}: {e}", Fore.RED))

        print()


def show_help_for_directory(cli_dir: Path, dir_parts: List[str]) -> bool:
    """
    If cli/<dir_parts>/ is a directory, show commands directly below it.
    """
    candidate_dir = cli_dir.joinpath(*dir_parts)
    if not candidate_dir.is_dir():
        return False

    commands = discover_commands(cli_dir)
    prefix = "/".join(dir_parts)

    print(color_text(f"Overview of commands in: {prefix}", Fore.CYAN + Style.BRIGHT))
    print()

    shown = False
    for cmd in commands:
        if (cmd.folder or "") == prefix:
            desc = extract_description_via_help(cmd.module)
            print(color_text(format_command_help(cmd.name, desc, indent=2), ""))
            shown = True

    return shown
