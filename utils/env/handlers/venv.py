"""VENV: effective venv directory (VIRTUAL_ENV if set, else INFINITO_VENV_FALLBACK).

VENV defaults to the infinito-owned venv path, not to whatever the
caller happens to have sourced (e.g. ``pkgmgr``). Callers that genuinely
want to point at a different venv can still override via the ``VENV``
env-var, which setdefault respects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "VENV"
COMMENT = "Effective venv directory (VIRTUAL_ENV if set, else INFINITO_VENV_FALLBACK)."


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    venv_base = eb.get("INFINITO_VENV_BASE") or "/opt/venvs"
    venv_name = eb.get("INFINITO_VENV_NAME") or "infinito"
    venv_fallback = f"{venv_base.rstrip('/')}/{venv_name}"
    eb.setdefault(KEY, venv_fallback, comment=COMMENT)
