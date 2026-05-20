"""Handler registry. ``ORDERED_HANDLERS`` is iterated by ``build_env()``.

Each handler module exposes ``apply(eb, ctx) -> None``. Cross-handler
data flows via :class:`utils.env.builder.EnvBuilder`; handlers must not
import each other.
"""

from __future__ import annotations

from . import (
    gha_passthrough,
    github_repository_owner,
    infinito_compile,
    infinito_container,
    infinito_docker_volume,
    infinito_image,
    infinito_image_repository,
    infinito_inventory,
    infinito_is_wsl2,
    infinito_package_cache_admin_password,
    infinito_package_cache_blobstore_max,
    infinito_package_cache_direct_mem,
    infinito_package_cache_heap,
    infinito_pull_policy,
    infinito_registry_cache_max_size,
    infinito_running_on_act,
    infinito_running_on_github,
    infinito_venv_base,
    infinito_venv_fallback,
    infinito_worker_cpu,
    infinito_worker_fetch,
    nix_config,
    passthrough,
    pip,
    python,
    venv,
)

ORDERED_HANDLERS = [
    passthrough,
    infinito_worker_cpu,
    infinito_worker_fetch,
    infinito_container,
    infinito_running_on_act,
    infinito_running_on_github,
    infinito_is_wsl2,
    infinito_venv_base,
    infinito_venv_fallback,
    venv,
    python,
    pip,
    infinito_inventory,
    gha_passthrough,
    infinito_pull_policy,
    infinito_docker_volume,
    github_repository_owner,
    infinito_image_repository,
    infinito_image,
    infinito_compile,
    nix_config,
    infinito_registry_cache_max_size,
    infinito_package_cache_heap,
    infinito_package_cache_direct_mem,
    infinito_package_cache_blobstore_max,
    infinito_package_cache_admin_password,
]

# Back-compat for tests/integration/meta/env/test_dotenv_generator.py
PASSTHROUGH_STATIC_KEYS = passthrough.STATIC_KEYS
GHA_STATIC_KEYS = gha_passthrough.STATIC_KEYS
