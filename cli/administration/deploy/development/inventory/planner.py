"""Matrix-deploy planner.

Pure functions only — they read role metadata via cached YAML helpers
and emit `PlanEntry` tuples. Two include-resolution modes share the
planner: strict variant-only when any primary ships `variants.yml`
(see `.variants`), and the legacy `CombinedResolver` fallback for
everything else (see `.legacy_resolver`). The submodules are referenced
through the package (`from . import variants, legacy_resolver`) so unit
tests can `mock.patch` them at the package-attribute level.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from utils.cache.applications import get_variants

from . import legacy_resolver, variants

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .spec import PlanEntry


def filter_plan_to_variant(
    plan: list[PlanEntry],
    variant: int | None,
) -> list[PlanEntry]:
    """Pin a matrix plan to a single round when `variant` is set.

    `variant=None` returns the plan unchanged (full-matrix mode). An
    explicit variant index is matched against the plan's round indices;
    if it's out of range, raises `ValueError` so callers can surface a
    clean operator-facing error rather than silently doing nothing.
    """
    if variant is None:
        return plan
    for entry in plan:
        if entry[0] == variant:
            return [entry]
    available = sorted(entry[0] for entry in plan)
    raise ValueError(f"variant {variant} out of range; available rounds: {available}")


def plan_dev_inventory_matrix(
    *,
    roles_dir: str,
    primary_apps: Sequence[str],
    base_inventory_dir: str,
) -> list[PlanEntry]:
    """Return ``[(round_index, inventory_dir, round_variants, include), ...]``.

    `total_rounds = max(variant_count)` across the **primary** apps the
    user named. In each round R, every primary uses variant R clamped
    to its own count; deps' round_variants are extended after include
    resolution so the inventory baker can pick the right variant per
    dep too.

    Two include-resolution modes share this planner:

    * **Variant-only mode** kicks in as soon as ANY primary ships a
      `meta/variants.yml` file. Each round's include is built strictly
      from the variant's merged `services:` block — only keys with
      literal `enabled: true` AND `shared: true` are pulled in (Jinja
      flags do NOT count, because `group_names` does not exist yet at
      build time). When multiple primaries declare the same service key
      at the same round with non-equal `(enabled, shared)` values, the
      planner raises a `ValueError` with the conflicting apps / round /
      key — variant-mode must stay deterministic.

    * **Default mode** (no primary has `variants.yml`) keeps the legacy
      `CombinedResolver` path which evaluates Jinja flags at deploy time
      against `group_names` and expands the include via both `run_after`
      and `shared:`-edges.

    Inventory paths are suffixed with `-<round>` only when
    `total_rounds > 1`, so single-variant deploys keep the historical
    unsuffixed path.

    Pure function — only reads `meta/services.yml` / `meta/variants.yml`
    via the cached YAML helpers; writes nothing.
    """
    if not primary_apps:
        raise ValueError("plan_dev_inventory_matrix: primary_apps must not be empty")
    variants_per_app = get_variants(roles_dir=roles_dir)
    primary_variant_counts = {
        app_id: max(1, len(variants_per_app.get(app_id) or [{}]))
        for app_id in primary_apps
    }
    total_rounds = max(primary_variant_counts.values(), default=1)
    base = str(base_inventory_dir).rstrip("/")

    roles_dir_path = Path(roles_dir)
    variant_only_mode = any(
        variants._has_explicit_variants(app_id, roles_dir_path)
        for app_id in primary_apps
    )

    plan: list[PlanEntry] = []
    for round_index in range(total_rounds):
        primary_round_variants = {
            app_id: round_index if round_index < count else 0
            for app_id, count in primary_variant_counts.items()
        }

        if variant_only_mode:
            raw_include = variants._resolve_round_include_variant_only(
                primary_apps=primary_apps,
                round_index=round_index,
                variants_per_app=variants_per_app,
                roles_dir=roles_dir_path,
            )
            variants._detect_variant_conflicts(
                include=raw_include,
                round_index=round_index,
                variants_per_app=variants_per_app,
            )
            round_include = variants._topo_sort_by_run_after(
                raw_include, roles_dir_path
            )
        else:
            services_overrides = legacy_resolver._build_services_overrides_for_round(
                roles_dir=roles_dir,
                round_index=round_index,
                primary_app_variants=primary_round_variants,
            )
            round_include = legacy_resolver._resolve_round_include(
                primary_apps=primary_apps,
                services_overrides=services_overrides,
            )
        # Extend round_variants with discovered deps' variants so deploy.py
        # and the inventory baker decide variant-cleanly per dep too.
        round_variants = dict(primary_round_variants)
        for dep in round_include:
            if dep in round_variants:
                continue
            dep_variants = variants_per_app.get(dep) or [{}]
            dep_count = max(1, len(dep_variants))
            round_variants[dep] = round_index if round_index < dep_count else 0

        inv_dir = f"{base}-{round_index}" if total_rounds > 1 else base
        plan.append((round_index, inv_dir, round_variants, round_include))
    return plan
