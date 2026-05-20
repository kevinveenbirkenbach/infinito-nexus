"""INFINITO_VENV_FALLBACK: derived venv path when VIRTUAL_ENV is unset:
``$INFINITO_VENV_BASE/$INFINITO_VENV_NAME``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "INFINITO_VENV_FALLBACK"
COMMENT = (
    "Derived venv path when VIRTUAL_ENV is unset: "
    "$INFINITO_VENV_BASE/$INFINITO_VENV_NAME."
)


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    venv_base = eb.get("INFINITO_VENV_BASE") or "/opt/venvs"
    venv_name = eb.get("INFINITO_VENV_NAME") or "infinito"
    eb.setdefault(KEY, f"{venv_base.rstrip('/')}/{venv_name}", comment=COMMENT)
