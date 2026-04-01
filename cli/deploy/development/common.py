from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from .deps import apps_with_deps, resolve_run_after

if TYPE_CHECKING:
    # Import only for type checking to avoid runtime import cycles.
    from .compose import Compose


def repo_root_from_here() -> Path:
    # <repo>/cli/deploy/development/common.py -> parents[3] == <repo>
    return Path(__file__).resolve().parents[3]


def ensure_distro_env(distro: str) -> None:
    # Keep env consistent with compose wrapper and other scripts
    os.environ["INFINITO_DISTRO"] = distro


def make_compose(*, distro: str) -> Compose:
    from .compose import Compose

    ensure_distro_env(distro)
    return Compose(repo_root=repo_root_from_here(), distro=distro)


def resolve_deploy_ids_for_app(compose: Compose, app_id: str) -> list[str]:
    deps = resolve_run_after(compose, app_id)
    return apps_with_deps(app_id, deps_role_names=deps)
