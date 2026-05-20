"""PIP: resolved pip invocation; usually ``$PYTHON -m pip``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "PIP"
COMMENT = "Resolved pip invocation; usually `$PYTHON -m pip`."


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    eb.setdefault(KEY, f"{eb.get('PYTHON')} -m pip", comment=COMMENT)
