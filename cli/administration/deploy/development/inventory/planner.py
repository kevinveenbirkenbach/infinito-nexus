"""Matrix-deploy planner.

Pure function — reads role metadata via cached YAML helpers and emits
``PlanEntry`` tuples; no filesystem side effects. The include set per
round is resolved by the ``CombinedResolver`` (see ``.legacy_resolver``):
each role contributes its own pulled-in providers and the include is
the union. A service-key is therefore pulled in as soon as ANY role in
the round-aware closure says it should be (literal ``True`` OR the
``"{{ '<role>' in group_names }}"`` Jinja form, both accepted by
``utils.roles.applications.services.registry.is_explicit_truth``); if
EVERY role marks it ``False`` it stays out of the include.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from utils.cache.applications import get_variants

from . import legacy_resolver

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

    ``total_rounds = max(variant_count)`` across the **primary** apps the
    user named. In round R every primary uses variant R clamped to its
    own count; transitive deps discovered for that round use R clamped
    to their own count too. The variant-aware resolver is invoked per
    round so the include set reflects the variant-merged topology —
    apps a variant pulls in via ``services.<X>.enabled: true`` appear
    in the include for that round (and not for rounds where they are
    not pulled).

    Inventory paths are suffixed with ``-<round>`` only when
    ``total_rounds > 1``, so single-variant deploys keep the historical
    unsuffixed path.
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

    plan: list[PlanEntry] = []
    for round_index in range(total_rounds):
        primary_round_variants = {
            app_id: round_index if round_index < count else 0
            for app_id, count in primary_variant_counts.items()
        }

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
