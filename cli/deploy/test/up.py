from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .compose import Compose


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = _repo_root_from_here()
    distro = os.environ.get("INFINITO_DISTRO", "arch")
    Compose(repo_root=repo_root, distro=distro).up()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
