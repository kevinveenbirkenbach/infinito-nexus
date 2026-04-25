"""Application-domain cache: variants, defaults, merged lookup.

Owns `_APPLICATIONS_DEFAULTS_CACHE`, `_VARIANTS_CACHE`, and
`_MERGED_APPLICATIONS_CACHE`. Public API: `get_application_defaults`,
`get_variants`, `get_merged_applications`. Strictly ansible-free at
import time so the GitHub Actions runner-host CLI path
(`cli.deploy.development.init` -> `plan_dev_inventory_matrix` ->
`get_variants`) keeps working without ansible installed.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Optional

from plugins.filter.merge_with_defaults import merge_with_defaults

from .base import (
    _RENDER_GUARD,
    _cache_key,
    _deep_merge,
    _load_yaml_mapping,
    _load_yaml_variant_list,
    _render_with_templar,
    _resolve_override_mapping,
    _resolve_roles_dir,
    _stable_variables_signature,
)


_APPLICATIONS_DEFAULTS_CACHE: dict[str, dict[str, Any]] = {}
_VARIANTS_CACHE: dict[str, dict[str, list[Any]]] = {}
_MERGED_APPLICATIONS_CACHE: dict[tuple, dict[str, Any]] = {}


def _build_role_base_config(
    role_dir: Path,
    roles_dir: Path,
) -> dict[str, Any]:
    """Return the post-augmentation `config/main.yml` payload for a
    role: `group_id` resolved, `users` references rewritten to
    `lookup('users', ...)`. Empty config collapses to `{}` (no
    overrides applied)."""
    # Pure-Python GID resolver — does NOT pull ansible. The previous
    # `ApplicationGidLookup().run([...])` call dragged
    # `ansible.plugins.lookup.LookupBase` into this code path and broke
    # `cli.deploy.development init` on the GitHub Actions runner host
    # (CI run 24935979190) where the runner Python ships without
    # ansible. The split lives in plugins/lookup/application_gid.py:
    # `compute_application_gid` is the pure helper, `LookupModule` is
    # the ansible-facing wrapper.
    from plugins.lookup.application_gid import compute_application_gid

    application_id = role_dir.name
    config_data = _load_yaml_mapping(role_dir / "config" / "main.yml")
    if not config_data:
        return {}

    group_id = compute_application_gid(application_id, str(roles_dir))
    config_data["group_id"] = group_id

    users_meta = _load_yaml_mapping(role_dir / "users" / "main.yml")
    users_data = users_meta.get("users", {})
    if isinstance(users_data, dict) and users_data:
        config_data["users"] = {
            user_key: "{{ lookup('users', " + repr(user_key) + ") }}"
            for user_key in users_data
        }
    return config_data


def _build_variants(roles_dir: Path) -> dict[str, list[Any]]:
    """Return ``{application_id: [variant_0, variant_1, ...]}``.

    Each variant is the role's `config/main.yml` payload deep-merged
    with the corresponding entry from
    `roles/<role>/meta/variants.yml`. A missing/empty
    `meta/variants.yml` collapses to a single empty variant so the
    role keeps its pre-variant behaviour. The single-variant case is
    equivalent to the legacy `_build_application_defaults` output.
    """
    variants: dict[str, list[Any]] = {}

    for config_file in sorted(roles_dir.glob("*/config/main.yml")):
        role_dir = config_file.parents[1]
        application_id = role_dir.name
        base_config = _build_role_base_config(role_dir, roles_dir)
        meta_path = role_dir / "meta" / "variants.yml"
        override_list = _load_yaml_variant_list(meta_path)
        role_variants: list[Any] = []
        for override in override_list:
            if base_config:
                role_variants.append(_deep_merge(base_config, override))
            else:
                # Role has no config/main.yml payload, but a variant list
                # MAY still legitimately produce an override-only result
                # (e.g. when a role declares its inventory entirely from
                # meta/variants.yml). Fall back to a deep copy of the
                # override so callers never observe shared mutable state.
                role_variants.append(copy.deepcopy(override))
        variants[application_id] = role_variants

    return {key: variants[key] for key in sorted(variants)}


def _build_application_defaults(roles_dir: Path) -> dict[str, Any]:
    """Backward-compatible shim: every consumer that historically saw
    one mapping per application now sees the FIRST variant (index 0).
    The full list is exposed via :func:`get_variants`."""
    return {
        application_id: copy.deepcopy(variant_list[0])
        for application_id, variant_list in _build_variants(roles_dir).items()
    }


def get_application_defaults(
    *, roles_dir: Optional[str | os.PathLike[str]] = None
) -> dict[str, Any]:
    resolved_roles_dir = _resolve_roles_dir(roles_dir=roles_dir)
    key = _cache_key(resolved_roles_dir)
    cached = _APPLICATIONS_DEFAULTS_CACHE.get(key)
    if cached is None:
        cached = _build_application_defaults(resolved_roles_dir)
        _APPLICATIONS_DEFAULTS_CACHE[key] = cached
    return copy.deepcopy(cached)


def get_variants(
    *, roles_dir: Optional[str | os.PathLike[str]] = None
) -> dict[str, list[Any]]:
    """Return ``{application_id: [variant_0, ...]}`` cached per
    ``roles_dir``. Each variant is the role's effective configuration
    after the corresponding `meta/variants.yml` override has been
    deep-merged on top of `config/main.yml`."""
    resolved_roles_dir = _resolve_roles_dir(roles_dir=roles_dir)
    key = _cache_key(resolved_roles_dir)
    cached = _VARIANTS_CACHE.get(key)
    if cached is None:
        cached = _build_variants(resolved_roles_dir)
        _VARIANTS_CACHE[key] = cached
    return copy.deepcopy(cached)


def get_merged_applications(
    *,
    variables: Optional[dict[str, Any]] = None,
    roles_dir: Optional[str | os.PathLike[str]] = None,
    templar: Any = None,
) -> dict[str, Any]:
    # Late import: `get_merged_users` lives in the sibling `users` module
    # and pulls user-domain machinery (token store, alias materialization,
    # etc.) that this module's other entry points don't need. Importing
    # at function scope keeps `import utils.cache.applications` cheap so
    # the runner-host CLI path can use `get_variants` without paying for
    # the user-domain transitive imports.
    from .users import get_merged_users

    variables = variables or {}
    resolved_roles_dir = _resolve_roles_dir(roles_dir=roles_dir)
    cache_key = (
        _cache_key(resolved_roles_dir),
        _stable_variables_signature(variables),
    )
    cached = _MERGED_APPLICATIONS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Defaults always come from variant 0 (= the legacy `config/main.yml`
    # payload, deep-merged with the empty `{}` entry). Per-round variant
    # overrides are baked into the inventory's `applications.<app>` block at
    # init time (see `cli.deploy.development.inventory.build_dev_inventory`)
    # and applied below as overrides on top of these defaults, so the deploy
    # stage needs no runtime variant selector: the inventory itself is
    # variant-resolved.
    defaults = get_application_defaults(roles_dir=resolved_roles_dir)

    overrides = _resolve_override_mapping(variables, "applications", templar=templar)

    merged = merge_with_defaults(defaults, overrides)

    if getattr(_RENDER_GUARD, "applications", False):
        # Re-entry via cross-lookup: return unrendered merged payload; the
        # outer templar will resolve remaining Jinja at use-site.
        return merged

    _RENDER_GUARD.applications = True
    try:
        raw_users = get_merged_users(
            variables=variables,
            roles_dir=roles_dir,
            templar=None,
        )
        rendered = _render_with_templar(
            merged,
            templar=templar,
            variables=variables,
            raw_applications=merged,
            raw_users=raw_users,
        )
    finally:
        _RENDER_GUARD.applications = False

    _MERGED_APPLICATIONS_CACHE[cache_key] = rendered
    return rendered


def _reset() -> None:
    _APPLICATIONS_DEFAULTS_CACHE.clear()
    _VARIANTS_CACHE.clear()
    _MERGED_APPLICATIONS_CACHE.clear()
