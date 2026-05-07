"""Compatibility wrapper.

This package was migrated from a flat module (roles_list.py) to a package layout:
  roles_list/__main__.py contains the original implementation.

We re-export the public API so existing imports keep working.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# `__main__` does `from . import PROJECT_ROOT` at import time, so the
# constant has to be defined first.
from . import __main__ as _main  # noqa: E402

__all__ = getattr(_main, "__all__", [n for n in dir(_main) if not n.startswith("_")])
globals().update({name: getattr(_main, name) for name in __all__})

# Prefer explicit __all__ if the original module defined it.
__all__ = getattr(_main, "__all__", [n for n in dir(_main) if not n.startswith("_")])
