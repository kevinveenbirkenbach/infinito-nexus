"""NIX_CONFIG: pass-through of the caller's NIX_CONFIG, when present."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "NIX_CONFIG"
COMMENT = "Pass-through of the caller's NIX_CONFIG, when present."


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    nix_config = os.environ.get("NIX_CONFIG", "")
    if nix_config:
        eb.set(KEY, nix_config, comment=COMMENT)
