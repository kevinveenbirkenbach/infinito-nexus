"""Variant-only matrix-deploy include resolution.

When ANY primary app ships a `roles/<app>/meta/variants.yml`, the matrix
planner switches into a strict mode: only services that the chosen
variant's merged `services:` block pins to literal `enabled: true` AND
`shared: true` become inventory groups. Jinja flags like
``"{{ 'web-svc-logout' in group_names }}"`` do NOT count because at
inventory-build time `group_names` does not exist yet (we are building
it). Apps must explicitly pin both flags in the variant block to land
as sibling groups.

This is intentionally asymmetric with the default (non-variant) path
in `.legacy_resolver`, which keeps using `CombinedResolver` to walk
both `run_after` and `shared:` edges and evaluates the Jinja flags at
deploy time when `group_names` is populated.

Expansion is direct, NOT recursive: a sibling app pulled in by a
primary does not itself expand further via its own variants.yml — only
primaries declare what's "on their level".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from utils.roles.mapping import ROLE_FILE_META_VARIANTS


def _has_explicit_variants(application_id: str, roles_dir: str | Path) -> bool:
    """True iff `roles/<application_id>/meta/variants.yml` exists on disk.

    Gate for variant-only mode. Apps without an explicit variants file
    keep their legacy `CombinedResolver` resolution path so the default
    build stays untouched.
    """
    return (Path(roles_dir) / application_id / ROLE_FILE_META_VARIANTS).is_file()


def _service_flag_pair(entry: Any) -> tuple[Any, Any]:
    """Return the (enabled, shared) pair from a merged service entry.

    Non-mapping entries collapse to (None, None) so conflict detection
    can compare apples-to-apples even when one app pins the entry to a
    primitive value and another pins a dict.
    """
    if not isinstance(entry, Mapping):
        return (None, None)
    return (entry.get("enabled"), entry.get("shared"))


def _service_keys_with_enabled_and_shared(merged_services: Any) -> list[str]:
    """Return service keys whose merged entry has BOTH `enabled is True`
    AND `shared is True` as literal Python booleans.

    The strict `is True` check is what disqualifies Jinja templates
    (which remain as strings in the merged payload because we never
    invoke a templar in variant-only mode).
    """
    if not isinstance(merged_services, Mapping):
        return []
    matches: list[str] = []
    for key, entry in merged_services.items():
        if not isinstance(entry, Mapping):
            continue
        if entry.get("enabled") is True and entry.get("shared") is True:
            matches.append(str(key))
    return matches


def _round_variant_payload(
    variant_list: Sequence[Any] | None, round_index: int
) -> Mapping[str, Any] | None:
    """Pick the variant payload for `round_index`, clamping to 0 when
    out of range. Returns `None` when the list is empty or the picked
    entry is not a mapping (defensive — `get_variants` already
    normalises, but this is a public-ish boundary)."""
    if not variant_list:
        return None
    idx = round_index if round_index < len(variant_list) else 0
    if not 0 <= idx < len(variant_list):
        return None
    payload = variant_list[idx]
    return payload if isinstance(payload, Mapping) else None


def _resolve_round_include_variant_only(
    *,
    primary_apps: Sequence[str],
    round_index: int,
    variants_per_app: Mapping[str, Sequence[Any]],
    roles_dir: Path,
) -> tuple[str, ...]:
    """Build the per-round include list under the strict variant-only rule.

    Direct (non-recursive) expansion: each primary contributes itself
    plus every service-key in its variant R `services:` block whose
    merged entry has literal `enabled: true` AND `shared: true`. Service
    keys are resolved to provider application_ids via
    `find_provider_roles` (canonical service registry, knows `provides:`
    aliases).

    Order: primaries appear in user-given order; each primary's
    direct siblings are appended immediately after. Topological run_after
    sorting is applied by the caller — this function only stabilises the
    declaration order.
    """
    # Late import to keep the host-side import surface lean — the lookup
    # walks every role's meta/services.yml to build the service registry
    # and that is too much for callers that never enter variant-only mode.
    from cli.administration.inventory.provision.services_disabler import (
        find_provider_roles,
    )

    out: list[str] = []
    seen: set[str] = set()

    for app_id in primary_apps:
        if app_id not in seen:
            out.append(app_id)
            seen.add(app_id)

        payload = _round_variant_payload(variants_per_app.get(app_id), round_index)
        if payload is None:
            continue

        merged_services = payload.get("services")
        service_keys = _service_keys_with_enabled_and_shared(merged_services)
        if not service_keys:
            continue

        provider_map = find_provider_roles(service_keys, roles_dir)
        for key in service_keys:
            provider_app_id = provider_map.get(key)
            if not provider_app_id or provider_app_id in seen:
                continue
            out.append(provider_app_id)
            seen.add(provider_app_id)

    return tuple(out)


def _detect_variant_conflicts(
    *,
    include: Sequence[str],
    round_index: int,
    variants_per_app: Mapping[str, Sequence[Any]],
) -> None:
    """Raise `ValueError` when two apps in `include` declare the same
    service key at `round_index` with non-equal `(enabled, shared)`
    values.

    Comparison uses Python equality on the merged values (the same
    payloads `get_variants` returns), so a Jinja string `"{{ ... }}"`
    versus a literal `True` IS a conflict — variant-mode is supposed
    to be deterministic, mixing pinned vs. dynamic flags across primaries
    would defeat that.
    """
    per_app: dict[str, Mapping[str, Any]] = {}
    for app_id in include:
        payload = _round_variant_payload(variants_per_app.get(app_id), round_index)
        if payload is None:
            continue
        services = payload.get("services")
        if isinstance(services, Mapping):
            per_app[app_id] = services

    app_ids = list(per_app)
    for i, a_id in enumerate(app_ids):
        for b_id in app_ids[i + 1 :]:
            a_services = per_app[a_id]
            b_services = per_app[b_id]
            common = set(a_services).intersection(b_services)
            for key in sorted(common):
                a_pair = _service_flag_pair(a_services[key])
                b_pair = _service_flag_pair(b_services[key])
                if a_pair == b_pair:
                    continue
                raise ValueError(
                    "Variant conflict at round "
                    f"{round_index}, key '{key}':\n"
                    f"  {a_id}: enabled={a_pair[0]!r}, shared={a_pair[1]!r}\n"
                    f"  {b_id}: enabled={b_pair[0]!r}, shared={b_pair[1]!r}"
                )


def _topo_sort_by_run_after(include: Sequence[str], roles_dir: Path) -> tuple[str, ...]:
    """Topologically sort `include` by each role's `run_after`.

    Edges that point to roles NOT in `include` are dropped — variant-only
    mode never EXPANDS via run_after, it only uses run_after to ORDER the
    apps the variant declared. Stable, deterministic order: items with
    no remaining in-degree are emitted in their original order.

    Falls back to the original include order on cycle.
    """
    from collections import deque

    from utils.roles.meta_lookup import get_role_run_after

    if not include:
        return ()

    include_set = set(include)
    deps_in: dict[str, set[str]] = {app: set() for app in include}
    edges_out: dict[str, list[str]] = {app: [] for app in include}

    for app_id in include:
        role_dir = roles_dir / app_id
        try:
            run_after = get_role_run_after(role_dir, role_name=app_id)
        except Exception:
            # Best-effort: a missing/malformed meta MUST NOT break the
            # planner, so a failed lookup collapses to "no dep".
            run_after = []
        for ra in run_after or []:
            if ra in include_set and ra != app_id:
                deps_in[app_id].add(ra)
                edges_out[ra].append(app_id)

    index_of = {app: i for i, app in enumerate(include)}
    queue: deque[str] = deque(
        sorted([app for app in include if not deps_in[app]], key=index_of.get)
    )
    sorted_apps: list[str] = []
    while queue:
        app = queue.popleft()
        sorted_apps.append(app)
        for nbr in edges_out[app]:
            deps_in[nbr].discard(app)
            if not deps_in[nbr]:
                queue.append(nbr)

    if len(sorted_apps) != len(include):
        # Cycle — preserve caller's declaration order as a safe fallback.
        return tuple(include)
    return tuple(sorted_apps)
