from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# `__main__` does `from . import PROJECT_ROOT` at import time, so the
# constant has to be defined first.
from . import __main__ as _main  # noqa: E402

# Expose configuration that tests monkeypatch
ROLES_DIR = _main.ROLES_DIR


def run(prefix: str, preview: bool = False, overwrite: bool = False):
    # sync patched value into the implementation module
    _main.ROLES_DIR = ROLES_DIR
    return _main.run(prefix=prefix, preview=preview, overwrite=overwrite)


def process_role(*args, **kwargs):
    _main.ROLES_DIR = ROLES_DIR
    return _main.process_role(*args, **kwargs)


def main():
    _main.ROLES_DIR = ROLES_DIR
    return _main.main()


def __getattr__(name: str):
    return getattr(_main, name)
