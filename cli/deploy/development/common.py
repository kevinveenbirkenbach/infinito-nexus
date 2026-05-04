from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from .deps import apps_with_deps, resolve_run_after

if TYPE_CHECKING:
    from .compose import Compose


# Mirrors INVENTORY_VARS_FILE from scripts/meta/env/inventory.sh; a unit
# test locks the two literals together so they cannot drift.
DEV_INVENTORY_VARS_FILE: str = os.environ.get(
    "INVENTORY_VARS_FILE", "inventories/development/default.yml"
)


VALID_DISTROS: tuple[str, ...] = ("arch", "debian", "ubuntu", "fedora", "centos")


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def compose_file_args() -> list[str]:
    """Compose `-f` flags shared by up and down flows."""
    from .profile import Profile

    out = ["-f", "compose.yml"]
    if Profile().registry_cache_active():
        out += ["-f", "compose/cache.override.yml"]
    return out


def cache_env_overrides() -> dict[str, str]:
    """Env vars consumed strictly by compose/cache.override.yml."""
    from .profile import Profile

    if not Profile().registry_cache_active():
        return {}

    ca_dir = os.environ.get("INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR", "").strip()
    if not ca_dir:
        raise SystemExit(
            "INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR is not set. Source "
            "scripts/meta/env/cache/package.sh (or scripts/meta/env/all.sh) "
            "before invoking cli.deploy.development."
        )
    return {
        "INFINITO_REGISTRY_CACHE_PROXY_CONF": "./compose/registry-cache/proxy.conf",
        "INFINITO_PACKAGE_CACHE_PIP_CONF": "./compose/package-cache/pip.conf",
        "INFINITO_PACKAGE_CACHE_NPMRC": "./compose/package-cache/npmrc",
        "INFINITO_PACKAGE_CACHE_APT_LIST": "./compose/package-cache/apt.list",
        "INFINITO_PACKAGE_CACHE_FRONTEND_CA_FILE": f"{ca_dir}/ca.crt",
    }


def resolve_distro() -> str:
    """Return INFINITO_DISTRO; raise SystemExit if missing or invalid."""
    distro = os.environ.get("INFINITO_DISTRO", "").strip()
    if not distro:
        raise SystemExit(
            "INFINITO_DISTRO is not set. Source scripts/meta/env/defaults.sh "
            "or export INFINITO_DISTRO=<arch|debian|ubuntu|fedora|centos> "
            "before invoking cli.deploy.development."
        )
    if distro not in VALID_DISTROS:
        raise SystemExit(
            f"INFINITO_DISTRO={distro!r} is not a valid distro. "
            f"Valid: {', '.join(VALID_DISTROS)}."
        )
    return distro


def resolve_container() -> str:
    """Return INFINITO_CONTAINER; raise SystemExit if unset."""
    container = os.environ.get("INFINITO_CONTAINER", "").strip()
    if not container:
        raise SystemExit(
            "INFINITO_CONTAINER is not set. Source scripts/meta/env/defaults.sh "
            "before invoking cli.deploy.development."
        )
    return container


def make_compose() -> Compose:
    from .compose import Compose

    distro = resolve_distro()
    # Surface env-script gap here rather than as a cryptic compose error later.
    resolve_container()
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
