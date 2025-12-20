from __future__ import annotations

from . import __main__ as _main

# Patchable entrypoint for tests
run_in_container = _main.run_in_container


def main() -> int:
    _main.run_in_container = run_in_container
    return _main.main()


def __getattr__(name: str):
    return getattr(_main, name)
