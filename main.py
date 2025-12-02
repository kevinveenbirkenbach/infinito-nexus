#!/usr/bin/env python3

import os
import subprocess
import sys
import textwrap
import threading
import signal
from datetime import datetime
import pty
from module_utils.sounds import Sound
import time

# Color support
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
except ImportError:
    class Dummy:
        def __getattr__(self, name): return ''
    Fore = Back = Style = Dummy()


def color_text(text, color):
    return f"{color}{text}{Style.RESET_ALL}"


def format_command_help(name, description, indent=2, col_width=36, width=80):
    prefix = " " * indent + f"{name:<{col_width - indent}}"
    wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent=prefix,
        subsequent_indent=" " * col_width
    )
    return wrapper.fill(description)


def list_cli_commands(cli_dir):
    """Recursively list all .py files under cli_dir that use argparse (without .py)."""
    cmds = []
    for root, _, files in os.walk(cli_dir):
        for f in files:
            if not f.endswith(".py") or f.startswith("__"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                if 'argparse' not in content:
                    continue
            except Exception:
                continue
            rel_dir = os.path.relpath(root, cli_dir)
            name = os.path.splitext(f)[0]
            if rel_dir == ".":
                cmd = (None, name)
            else:
                cmd = (rel_dir.replace(os.sep, "/"), name)
            cmds.append(cmd)
    return sorted(cmds, key=lambda x: (x[0] or "", x[1]))


def extract_description_via_help(cli_script_path):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        cli_dir = os.path.join(script_dir, "cli")
        rel = os.path.relpath(cli_script_path, cli_dir)
        module = "cli." + rel[:-3].replace(os.sep, ".")

        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("usage:"):
                continue
            if not line.strip():
                for j in range(i+1, len(lines)):
                    desc = lines[j].strip()
                    if desc:
                        return desc
        return "-"
    except Exception:
        return "-"

def show_full_help_for_all(cli_dir, available):
    """
    Print the full --help output for all discovered CLI commands.
    """
    print(color_text("Infinito.Nexus CLI – Full Help Overview", Fore.CYAN + Style.BRIGHT))
    print()

    for folder, cmd in available:
        # Build module path (cli.<folder>.<cmd>)
        if folder:
            rel = os.path.join(folder, f"{cmd}.py")
        else:
            rel = f"{cmd}.py"

        module = "cli." + rel[:-3].replace(os.sep, ".")

        header_path = f"{folder + '/' if folder else ''}{cmd}.py"
        print(color_text("=" * 80, Fore.MAGENTA))
        print(color_text(f"Command: {header_path}", Fore.MAGENTA + Style.BRIGHT))
        print(color_text("-" * 80, Fore.MAGENTA))

        try:
            result = subprocess.run(
                [sys.executable, "-m", module, "--help"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(color_text(result.stderr.rstrip(), Fore.RED))
        except Exception as e:
            print(color_text(f"Failed to get help for {header_path}: {e}", Fore.RED))

        print()  # extra spacer between commands

def git_clean_repo():
    subprocess.run(['git', 'clean', '-Xfd'], check=True)


def play_start_intro():
    Sound.play_start_sound()
    Sound.play_infinito_intro_sound()


from multiprocessing import Process, get_start_method, set_start_method
import time

def _call_sound(method_name: str):
   # Re-import inside child to (re)init audio backend cleanly under 'spawn'
    from module_utils.sounds import Sound as _Sound
    getattr(_Sound, method_name)()

def _play_in_child(method_name: str) -> bool:
    p = Process(target=_call_sound, args=(method_name,))
    p.start(); p.join()
    if p.exitcode != 0:
        try:
            # Sichtbare Diagnose, wenn das Kind crasht/fehlschlägt
            print(color_text(f"[sound] child '{method_name}' exitcode={p.exitcode}", Fore.YELLOW))
        except Exception:
            pass
    return p.exitcode == 0

def failure_with_warning_loop(no_signal, sound_enabled, alarm_timeout=60):
    """
    Plays a warning sound in a loop until timeout; Ctrl+C stops earlier.
    Sound playback is isolated in a child process to avoid segfaulting the main process.
    """
    if not no_signal:
        # Try the failure jingle once; ignore failures
        _play_in_child("play_finished_failed_sound")

    print(color_text("Warning: command failed. Press Ctrl+C to stop warnings.", Fore.RED))
    start = time.monotonic()
    try:
        while time.monotonic() - start <= alarm_timeout:
            if no_signal:
                time.sleep(0.5)
                continue

            ok = _play_in_child("play_warning_sound")
            # If audio stack is broken, stay silent but avoid busy loop
            if not ok:
                time.sleep(0.8)
        print(color_text(f"Alarm aborted after {alarm_timeout} seconds.", Fore.RED))
        sys.exit(1)
    except KeyboardInterrupt:
        print(color_text("Warnings stopped by user.", Fore.YELLOW))
        sys.exit(1)

if __name__ == "__main__":
    # IMPORTANT: use 'spawn' so the child re-initializes audio cleanly
    try:
        if get_start_method(allow_none=True) != "spawn":
            set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    # Prefer system audio backend by default (prevents simpleaudio segfaults in child processes)
    os.environ.setdefault("INFINITO_AUDIO_BACKEND", "system")

    
    # Parse flags
    sound_enabled = '--sound' in sys.argv and (sys.argv.remove('--sound') or True)
    no_signal = '--no-signal' in sys.argv and (sys.argv.remove('--no-signal') or True)
    # Guaranty that --log is passed to deploy command
    log_enabled = '--log' in sys.argv
    if log_enabled and (len(sys.argv) < 2 or sys.argv[1] != 'deploy'):
        sys.argv.remove('--log')
    git_clean = '--git-clean' in sys.argv and (sys.argv.remove('--git-clean') or True)
    infinite = '--infinite' in sys.argv and (sys.argv.remove('--infinite') or True)
    help_all = '--help-all' in sys.argv and (sys.argv.remove('--help-all') or True)
    alarm_timeout = 60
    if '--alarm-timeout' in sys.argv:
        i = sys.argv.index('--alarm-timeout')
        try:
            alarm_timeout = int(sys.argv[i+1])
            del sys.argv[i:i+2]
        except Exception:
            print(color_text("Invalid --alarm-timeout value!", Fore.RED))
            sys.exit(1)

    # Play intro melody if requested
    if sound_enabled:
        threading.Thread(target=play_start_intro, daemon=True).start()

    script_dir = os.path.dirname(os.path.realpath(__file__))
    cli_dir = os.path.join(script_dir, "cli")
    os.chdir(script_dir)

    if git_clean:
        git_clean_repo()

    # Collect available commands
    available = list_cli_commands(cli_dir)
    args = sys.argv[1:]

    # Global "show help for all commands" mode
    if help_all:
        show_full_help_for_all(cli_dir, available)
        sys.exit(0)


    # Global help
    if not args or args[0] in ('-h', '--help'):
        print(color_text("Infinito.Nexus CLI 🦫🌐🖥️", Fore.CYAN + Style.BRIGHT))
        print()
        print(color_text("Your Gateway to Automated IT Infrastructure Setup", Style.DIM))
        print()
        print(color_text(
            "Usage: infinito "
            "[--sound] "
            "[--no-signal] "
            "[--log] "
            "[--git-clean] "
            "[--infinite] "
            "[--help-all] "
            "[--alarm-timeout <seconds>] "
            "[-h|--help] "
            "<command> [options]",
            Fore.GREEN
        ))
        print()
        # Use bright style for headings
        print(color_text("Options:", Style.BRIGHT))
        print(color_text("  --sound           Play startup melody and warning sounds", Fore.YELLOW))
        print(color_text("  --no-signal       Suppress success/failure signals", Fore.YELLOW))
        print(color_text("  --log             Log all proxied command output to logfile.log", Fore.YELLOW))
        print(color_text("  --git-clean       Remove all Git-ignored files before running", Fore.YELLOW))
        print(color_text("  --infinite        Run the proxied command in an infinite loop", Fore.YELLOW))
        print(color_text("  --help-all        Show full --help for all CLI commands", Fore.YELLOW))
        print(color_text("  --alarm-timeout   Stop warnings and exit after N seconds (default: 60)", Fore.YELLOW))
        print(color_text("  -h, --help        Show this help message and exit", Fore.YELLOW))
        print()
        print(color_text("Available commands:", Style.BRIGHT))
        print()

        current_folder = None
        for folder, cmd in available:
            if folder != current_folder:
                if folder:
                    print(color_text(f"{folder}/", Fore.MAGENTA))
                    print()
                current_folder = folder
            desc = extract_description_via_help(
                os.path.join(cli_dir, *(folder.split('/') if folder else []), f"{cmd}.py")
            )
            print(color_text(format_command_help(cmd, desc, indent=2), ''), "\n")

        print()
        print(color_text(
            "🔗  You can chain subcommands by specifying nested directories,",
            Fore.CYAN
        ))
        print(color_text(
            "    e.g. `infinito build defaults users` →",
            Fore.CYAN
        ))
        print(color_text(
            "    corresponds to `cli/build/defaults/users.py`.",
            Fore.CYAN
        ))
        print()
        print(color_text(
            "Infinito.Nexus is a product of Kevin Veen-Birkenbach, https://cybermaster.space .\n",
            Style.DIM
        ))
        print(color_text(
            "Test and use productively on https://infinito.nexus .\n",
            Style.DIM
        ))
        print(color_text(
            "For commercial use, a license agreement with Kevin Veen-Birkenbach is required. \n",
            Style.DIM
        ))
        print(color_text("License: https://s.infinito.nexus/license", Style.DIM))
        print()
        print(color_text("🎉🌈 Happy IT Infrastructuring! 🚀🔧✨", Fore.MAGENTA + Style.BRIGHT))
        print()
        sys.exit(0)

    # Directory-specific help
    if len(args) > 1 and args[-1] in ('-h', '--help'):
        dir_parts = args[:-1]
        candidate_dir = os.path.join(cli_dir, *dir_parts)
        if os.path.isdir(candidate_dir):
            print(color_text(
                f"Overview of commands in: {'/'.join(dir_parts)}",
                Fore.CYAN + Style.BRIGHT
            ))
            print()
            for folder, cmd in available:
                if folder == "/".join(dir_parts):
                    desc = extract_description_via_help(
                        os.path.join(candidate_dir, f"{cmd}.py")
                    )
                    print(color_text(format_command_help(cmd, desc, indent=2), ''))
            sys.exit(0)

    # Per-command help
    for n in range(len(args), 0, -1):
        candidate = os.path.join(cli_dir, *args[:n]) + ".py"
        if os.path.isfile(candidate) and len(args) > n and args[n] in ('-h', '--help'):
            rel = os.path.relpath(candidate, cli_dir)
            module = "cli." + rel[:-3].replace(os.sep, ".")
            subprocess.run([sys.executable, "-m", module, args[n]])
            sys.exit(0)

    # Resolve script path
    script_path = None
    cli_args = []
    module = None
    for n in range(len(args), 0, -1):
        candidate = os.path.join(cli_dir, *args[:n]) + ".py"
        if os.path.isfile(candidate):
            script_path = candidate
            cli_args = args[n:]
            rel = os.path.relpath(candidate, cli_dir)
            module = "cli." + rel[:-3].replace(os.sep, ".")
            break

    if not module:
        print(color_text(f"Error: command '{' '.join(args)}' not found.", Fore.RED))
        sys.exit(1)

    log_file = None
    if log_enabled:
        log_dir = os.path.join(script_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        log_file_path = os.path.join(log_dir, f'{timestamp}.log')
        log_file = open(log_file_path, 'a', encoding='utf-8')
        print(color_text(f"Tip: Log file created at {log_file_path}", Fore.GREEN))

    full_cmd = [sys.executable, "-m", module] + cli_args

    def run_once():
        try:
            if log_enabled:
                master_fd, slave_fd = pty.openpty()
                proc = subprocess.Popen(
                    full_cmd,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    text=True
                )
                os.close(slave_fd)
                import errno
                with os.fdopen(master_fd) as master:
                    try:
                        for line in master:
                            ts = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                            log_file.write(f"{ts} {line}")
                            log_file.flush()
                            print(line, end='')
                    except OSError as e:
                        if e.errno != errno.EIO:
                            raise
                proc.wait()
                rc = proc.returncode
            else:
                proc = subprocess.Popen(full_cmd)
                proc.wait()
                rc = proc.returncode

            if log_file:
                log_file.close()

            if rc != 0:
                failure_with_warning_loop(no_signal, sound_enabled, alarm_timeout)
                sys.exit(rc)
            else:
                if not no_signal:
                    Sound.play_finished_successfully_sound()
                return True
        except Exception as e:
            print(color_text(f"Exception running command: {e}", Fore.RED))
            failure_with_warning_loop(no_signal, sound_enabled, alarm_timeout)
            sys.exit(1)

    if infinite:
        print(color_text("Starting infinite execution mode...", Fore.CYAN))
        count = 1
        while True:
            print(color_text(f"Run #{count}", Style.BRIGHT))
            run_once()
            count += 1
    else:
        run_once()
        sys.exit(0)
