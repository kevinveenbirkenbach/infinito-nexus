from __future__ import annotations

import os
import sys
import time
import traceback
from multiprocessing import Process, get_start_method, set_start_method

from cli.core.colors import Fore, color_text


def init_multiprocessing() -> None:
    # IMPORTANT: use spawn so the child re-initializes audio cleanly
    try:
        if get_start_method(allow_none=True) != "spawn":
            set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    # Prefer system audio backend by default (prevents simpleaudio segfaults in child processes)
    os.environ.setdefault("INFINITO_AUDIO_BACKEND", "system")


def play_start_intro_async() -> None:
    # local import to keep module import side effects small
    from module_utils.sounds import Sound

    Sound.play_start_sound()
    Sound.play_infinito_intro_sound()


def _call_sound(method_name: str) -> None:
    from module_utils.sounds import Sound as _Sound

    getattr(_Sound, method_name)()


def play_sound_in_child(method_name: str) -> bool:
    p = Process(target=_call_sound, args=(method_name,))
    p.start()
    p.join()
    if p.exitcode != 0:
        try:
            print(
                color_text(
                    f"[sound] child '{method_name}' exitcode={p.exitcode}", Fore.YELLOW
                )
            )
        except Exception as e:
            print(
                f"Error while attempting to print sound process warning: {e}",
                file=sys.stderr,
            )
            traceback.print_exc()
    return p.exitcode == 0


def failure_with_warning_loop(
    no_signal: bool, sound_enabled: bool, alarm_timeout: int = 60
) -> None:
    """
    Plays a warning sound in a loop until timeout; Ctrl+C stops earlier.
    Sound playback is isolated in a child process to avoid segfaulting the main process.
    """
    if not no_signal:
        # Try the failure jingle once; ignore failures
        play_sound_in_child("play_finished_failed_sound")

    print(
        color_text("Warning: command failed. Press Ctrl+C to stop warnings.", Fore.RED)
    )
    start = time.monotonic()
    try:
        while time.monotonic() - start <= alarm_timeout:
            if no_signal:
                time.sleep(0.5)
                continue

            ok = play_sound_in_child("play_warning_sound")
            # If audio stack is broken, stay silent but avoid busy loop
            if not ok:
                time.sleep(0.8)

        print(color_text(f"Alarm aborted after {alarm_timeout} seconds.", Fore.RED))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print(color_text("Warnings stopped by user.", Fore.YELLOW))
        raise SystemExit(1)
