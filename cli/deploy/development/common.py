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


VALID_DISTROS: tuple[str, ...] = ("arch", "debian", "ubuntu", "fedora", "centos")


def repo_root_from_here() -> Path:
    # <repo>/cli/deploy/development/common.py -> parents[3] == <repo>
    return Path(__file__).resolve().parents[3]


def compose_file_args() -> list[str]:
    """SPOT for the `docker compose -f ...` flag list. Both `up` and
    `down` flows MUST use this so they target the exact same set of
    compose files; otherwise `down` leaves orphans (the cache override
    is added on `up` but missed on `down`, or vice versa).

    The base `compose.yml` is included always; the cache override is
    layered on top only when the `cache` stack is active.
    """
    from .profile import Profile

    out = ["-f", "compose.yml"]
    if Profile().registry_cache_active():
        out += ["-f", "compose/cache.override.yml"]
    return out


def cache_env_overrides() -> dict[str, str]:
    """SPOT for env vars the cache override file (`compose/cache.override.yml`)
    expects strictly via `${VAR:?…}`. The values are repo-relative bind
    sources for the cache client snippets plus the resolved CA file path.

    Both `cli.deploy.development.compose` (up flow) and
    `cli.deploy.development.down` (down flow) MUST call this before
    invoking `docker compose` so the `${VAR:?…}` expansions resolve
    identically across both flows. Without a single SPOT the two
    flows can drift, and `make down` then fails with a
    "required variable missing" error before reaching the actual
    teardown step.

    Returns an empty dict when the cache stack is inactive (CI runs)
    so the override file is not loaded and no env vars are needed.
    """
    from .profile import Profile

    if not Profile().registry_cache_active():
        return {}

    # SPOT for the host CA directory is `scripts/meta/env/cache/package.sh`
    # (sourced via BASH_ENV in every Makefile recipe). Refusing to fall
    # back here keeps the SPOT contract: a missing env var means the
    # env layer was not sourced, and silently picking a duplicate
    # literal default would let the two SPOTs drift.
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
    """Return the current INFINITO_DISTRO. Single SPOT for the value.

    The env var is the only input — all CLI subcommands rely on it
    (callers source `scripts/meta/env/defaults.sh` before invocation).
    Raises SystemExit when unset or invalid so a missing setup never
    silently picks the wrong distro.
    """
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
    """Return the current INFINITO_CONTAINER. Single SPOT for the value.

    The env var is kept in lock-step with INFINITO_DISTRO by
    `scripts/meta/env/defaults.sh` (always-derived block outside its
    load-once guard); callers that change INFINITO_DISTRO MUST re-source
    defaults.sh so this stays consistent. Raises SystemExit when unset
    so a missing setup never silently exec's the wrong container.
    """
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
    # Early-fail guard so a missing scripts/meta/env/defaults.sh source
    # surfaces here instead of as a confusing
    # `compose.yml: required variable INFINITO_CONTAINER missing` later.
    # The two env vars must travel together; defaults.sh keeps them in sync.
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
