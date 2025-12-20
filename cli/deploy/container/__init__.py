"""Compatibility wrapper.

This package was migrated from a flat module (container.py) to a package layout:
  container/__main__.py contains the original implementation.

We re-export the public API so existing imports keep working.
"""

from __future__ import annotations

from . import __main__ as _main
from .__main__ import *  # noqa: F401,F403

# Prefer explicit __all__ if the original module defined it.
__all__ = getattr(_main, "__all__", [n for n in dir(_main) if not n.startswith("_")])
