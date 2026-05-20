"""INFINITO_COMPILE: 1 = build infinito locally inside the container on
entry; 0 = use the pulled image as-is. On GHA we force 0 (pull the
published image, don't rebuild locally). Locally the default.env default
``1`` carries through."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "INFINITO_COMPILE"
COMMENT = (
    "1 = build infinito locally inside the container on entry; 0 = use "
    "the pulled image as-is."
)


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    if not ctx.on_gha:
        return
    eb.set(KEY, "0", comment=COMMENT)
