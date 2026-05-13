"""SPOT for development inventory creation.

Anything that wants to materialise the development inventory MUST go
through :func:`build_dev_inventory` (single folder) or
:func:`build_dev_inventory_matrix` (one folder per matrix-deploy round).
Both flow through :class:`DevInventorySpec` and own:

* the SPOT vars-file (``DEV_INVENTORY_VARS_FILE``),
* per-app variant baking (each role's ``meta/variants.yml`` is resolved
  at build time and emitted as ``applications.<app>`` overrides into
  the inventory's ``host_vars``, with variant 0 as the fallback for
  apps without ``meta/variants.yml``),
* the vault password file.

The deploy wrapper consumes :func:`plan_dev_inventory_matrix` to know
which folder to deploy against in each round; the planner is a pure
function so wrapper and init step compute the same plan independently.

Internal layout (one module per responsibility):

* :mod:`.spec`            — :class:`DevInventorySpec` + ``PlanEntry`` type
* :mod:`.payload`         — variant payload pick + ``--vars`` bake
* :mod:`.legacy_resolver` — ``CombinedResolver`` fallback path
* :mod:`.variants`        — strict variant-only include resolution
* :mod:`.planner`         — :func:`plan_dev_inventory_matrix` (gates the two modes)
* :mod:`.builder`         — :func:`build_dev_inventory` + matrix orchestrator

The private helpers (``_resolve_round_include`` and friends) are
re-exported below because unit tests historically patch them under this
package path. New tests SHOULD patch the submodule path directly
(e.g. ``inventory.variants._resolve_round_include_variant_only``).
"""

from __future__ import annotations

from .builder import build_dev_inventory, build_dev_inventory_matrix
from .legacy_resolver import _build_services_overrides_for_round, _resolve_round_include
from .payload import _bake_overrides, _resolve_variant_payloads
from .planner import filter_plan_to_variant, plan_dev_inventory_matrix
from .spec import DevInventorySpec, PlanEntry
from .variants import (
    _detect_variant_conflicts,
    _has_explicit_variants,
    _resolve_round_include_variant_only,
    _service_flag_pair,
    _service_keys_with_enabled_and_shared,
    _topo_sort_by_run_after,
)

# Note: private helper names (leading underscore) appear in `__all__` ONLY
# to silence ruff's F401 "unused import" — they are re-exported here so
# tests that historically import them from the package root keep working.
# New tests SHOULD patch the submodule path directly
# (e.g. ``inventory.variants._has_explicit_variants``) rather than the
# re-export.
__all__ = [
    "DevInventorySpec",
    "PlanEntry",
    "_bake_overrides",
    "_build_services_overrides_for_round",
    "_detect_variant_conflicts",
    "_has_explicit_variants",
    "_resolve_round_include",
    "_resolve_round_include_variant_only",
    "_resolve_variant_payloads",
    "_service_flag_pair",
    "_service_keys_with_enabled_and_shared",
    "_topo_sort_by_run_after",
    "build_dev_inventory",
    "build_dev_inventory_matrix",
    "filter_plan_to_variant",
    "plan_dev_inventory_matrix",
]
