from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from .deps import apps_with_deps, resolve_run_after

if TYPE_CHECKING:
    # Import only for type checking to avoid runtime import cycles.
    from .compose import Compose


# SPOT: canonical repo-relative path to the development vars file that
# `infinito create inventory --vars-file <...>` consumes. Mirrors
# `INVENTORY_VARS_FILE` from scripts/meta/env/inventory.sh; the bash file
# is the SPOT-of-record for callers that go through the deploy chain
# (env is set before Python runs), and the literal here is the fallback
# for direct/test invocations that bypass that chain. A unit test locks
# both literals together so they cannot silently drift.
DEV_INVENTORY_VARS_FILE: str = os.environ.get(
    "INVENTORY_VARS_FILE", "inventories/development/default.yml"
)


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


def resolve_deploy_ids_for_apps(compose: Compose, app_spec: str) -> list[str]:
    """Resolve deploy ids for one or more space- or comma-separated app ids."""
    app_ids = [a.strip() for a in app_spec.replace(",", " ").split() if a.strip()]
    result: list[str] = []
    for app_id in app_ids:
        for dep in resolve_deploy_ids_for_app(compose, app_id):
            if dep not in result:
                result.append(dep)
    return result
