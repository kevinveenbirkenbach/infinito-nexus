from __future__ import annotations

from . import __main__ as _main

from .modes import _parse_bool_literal  # noqa: F401

# Keep the main entrypoint patchable / importable
main = _main.main

__all__ = ["main", "_parse_bool_literal"]
