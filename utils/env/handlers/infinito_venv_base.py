"""INFINITO_VENV_BASE precedence:

1. An active VIRTUAL_ENV pins the base to its parent (caller is already
   inside a managed venv, respect it).
2. The default.env default (typically ``/opt/venvs``) wins when it is
   user-writable -- this is the container path.
3. Otherwise fall back to ``$HOME/.venvs`` so a non-root host user can
   create the venv without sudo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from utils.env.runtime import is_user_writable

if TYPE_CHECKING:
    from utils.env.builder import BuildContext, EnvBuilder

KEY = "INFINITO_VENV_BASE"


def apply(eb: EnvBuilder, ctx: BuildContext) -> None:
    comment = ctx.static_comments.get(KEY, "")
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    if virtual_env:
        eb.set(KEY, str(Path(virtual_env).parent) + "/", comment=comment)
    elif not is_user_writable(eb.get(KEY) or "/opt/venvs"):
        eb.set(KEY, str(Path.home() / ".venvs") + "/", comment=comment)
