"""PYTHON: absolute path to the venv's python (or ``python3`` fallback)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "PYTHON"
COMMENT = "Absolute path to the venv's python (or `python3` fallback)."


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    default_python = f"{eb.get('VENV').rstrip('/')}/bin/python"
    eb.setdefault(
        KEY,
        default_python if Path(default_python).exists() else "python3",
        comment=COMMENT,
    )
