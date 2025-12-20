from __future__ import annotations

from . import __main__ as _main
from .__main__ import *  # noqa: F401,F403

# Explicitly re-export private helpers required by unit tests
from .__main__ import _parse_bool_literal  # noqa: F401

__all__ = getattr(_main, "__all__", [n for n in dir(_main) if not n.startswith("_")])
