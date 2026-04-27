"""SPOT for development inventory creation.

Anything that wants to materialise the development inventory MUST go
through `build_dev_inventory` (single folder) or
`build_dev_inventory_matrix` (one folder per matrix-deploy round). Both
flow through `DevInventorySpec` and own:

* the SPOT vars-file (`DEV_INVENTORY_VARS_FILE`),
* per-app variant baking (each role's `meta/variants.yml` is resolved at
  build time and emitted as `applications.<app>` overrides into the
  inventory's `host_vars`, with variant 0 as the fallback for apps
  without `meta/variants.yml`),
* the vault password file.

The deploy wrapper consumes `plan_dev_inventory_matrix` to know which
folder to deploy against in each round; the planner is a pure function
so wrapper and init step compute the same plan independently.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from utils.cache.applications import get_variants

from .common import DEV_INVENTORY_VARS_FILE
from .mirrors import generate_ci_mirrors_file, should_use_mirrors_on_ci

if TYPE_CHECKING:
    from .compose import Compose


@dataclass(frozen=True)
class DevInventorySpec:
    """Everything `infinito create inventory` needs to materialise one
    development inventory folder.

    `extra_vars` wins over the implicit `STORAGE_CONSTRAINED` / `RUNTIME`
    overrides so callers (and tests) keep the documented "user-provided
    vars always win" behaviour without re-implementing the merge.

    `active_variants` is the per-app variant index for the round this
    folder represents. Apps absent from the mapping (or with an out-of-
    range index) fall back to variant 0. The resolved variant payload
    for every app in `include` is baked into the inventory as an
    `applications.<app>` override, so the deploy stage no longer needs
    a runtime variant selector — the inventory itself is variant-resolved.
    """

    inventory_dir: str
    include: tuple[str, ...]
    storage_constrained: bool
    runtime: str
    extra_vars: Mapping[str, Any] | None = None
    services_disabled: str = ""
    active_variants: Mapping[str, int] | None = None

    def __post_init__(self) -> None:
        if not self.include:
            raise ValueError("DevInventorySpec.include must not be empty")
        if not isinstance(self.include, tuple):
            object.__setattr__(self, "include", tuple(self.include))

    def overrides(self) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "STORAGE_CONSTRAINED": bool(self.storage_constrained),
            "RUNTIME": self.runtime,
        }
        if self.extra_vars:
            merged.update(self.extra_vars)
        return merged

    def variant_selectors(self) -> dict[str, int]:
        return dict(self.active_variants or {})

    def inventory_root(self) -> str:
        return str(self.inventory_dir).rstrip("/")


def _resolve_variant_payloads(
    *,
    roles_dir: str,
    include: Sequence[str],
    active_variants: Mapping[str, int],
) -> dict[str, Any]:
    """Return ``{app_id: variant_payload}`` for the requested round.

    Apps without `meta/variants.yml` collapse to a single empty variant
    in the loader, so this just picks variant 0 (= `meta/services.yml`
    unchanged) for them. Out-of-range indices clamp to 0.
    """
    variants_per_app = get_variants(roles_dir=roles_dir)
    resolved: dict[str, Any] = {}
    for app_id in include:
        variant_list = variants_per_app.get(app_id) or [{}]
        if not variant_list:
            continue
        index = active_variants.get(app_id, 0)
        if not 0 <= index < len(variant_list):
            index = 0
        resolved[app_id] = variant_list[index]
    return resolved


def _bake_overrides(
    *,
    base_overrides: Mapping[str, Any],
    variant_payloads: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge the per-app variant payloads under `applications:` into the
    `--vars` JSON the init step will hand to `infinito create inventory`.
    Caller-supplied `extra_vars` (already inside `base_overrides`) win
    over the variant bake when the same key is set on both sides — that
    matches the existing "user vars always win" rule."""
    merged: dict[str, Any] = dict(base_overrides)
    if not variant_payloads:
        return merged
    existing_apps = merged.get("applications")
    if not isinstance(existing_apps, Mapping):
        existing_apps = {}
    apps: dict[str, Any] = {
        app_id: payload for app_id, payload in variant_payloads.items()
    }
    # Caller-supplied `applications.*` entries deep-overlay the variant
    # payload so overrides like `applications.web-app-foo.feature_flag` from
    # `--vars` still take precedence.
    for app_id, override in existing_apps.items():
        base_payload = apps.get(app_id)
        if isinstance(base_payload, Mapping) and isinstance(override, Mapping):
            apps[app_id] = {**base_payload, **override}
        else:
            apps[app_id] = override
    merged["applications"] = apps
    return merged


def build_dev_inventory(compose: Compose, spec: DevInventorySpec) -> None:
    """Build the inventory folder described by `spec` and ensure its
    vault password file exists. Two side-effects, no return value: after
    this call, `spec.inventory_dir` contains a complete, variant-resolved
    inventory.
    """
    inv_root = spec.inventory_root()

    variant_payloads = _resolve_variant_payloads(
        roles_dir=str(compose.repo_root / "roles"),
        include=spec.include,
        active_variants=spec.variant_selectors(),
    )
    vars_payload = _bake_overrides(
        base_overrides=spec.overrides(),
        variant_payloads=variant_payloads,
    )

    cmd = [
        "infinito",
        "create",
        "inventory",
        inv_root,
        "--host",
        "localhost",
        "--ssl-disabled",
        "--vars-file",
        DEV_INVENTORY_VARS_FILE,
        "--vars",
        json.dumps(vars_payload, sort_keys=True),
        "--include",
        ",".join(spec.include),
    ]

    if should_use_mirrors_on_ci():
        mirrors_file = generate_ci_mirrors_file(compose, inventory_dir=inv_root)
        cmd += ["--mirror", mirrors_file]

    extra_env: dict[str, str] = {}
    if spec.services_disabled:
        extra_env["SERVICES_DISABLED"] = spec.services_disabled

    compose.exec(
        cmd,
        check=True,
        workdir="/opt/src/infinito",
        extra_env=extra_env or None,
    )
    _ensure_vault_password_file(compose, inventory_dir=inv_root)


def filter_plan_to_variant(
    plan: list[tuple[int, str, dict[str, int]]],
    variant: int | None,
) -> list[tuple[int, str, dict[str, int]]]:
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
    available = sorted(idx for idx, _, _ in plan)
    raise ValueError(f"variant {variant} out of range; available rounds: {available}")


def plan_dev_inventory_matrix(
    *,
    roles_dir: str,
    include: Sequence[str],
    base_inventory_dir: str,
) -> list[tuple[int, str, dict[str, int]]]:
    """Return ``[(round_index, inventory_dir, round_variants), ...]``.

    `total_rounds = max(variant_count)` across the included apps. In each
    round R, every app uses variant index R when its variant list is long
    enough, otherwise variant 0 (the legacy `meta/services.yml` payload).
    Inventory paths are suffixed with `-<round>` only when `total_rounds
    > 1`, so single-variant deploys keep the historical unsuffixed path.

    Pure function — does not touch disk.
    """
    if not include:
        raise ValueError("plan_dev_inventory_matrix: include must not be empty")
    variants_per_app = get_variants(roles_dir=roles_dir)
    variant_counts = {
        app_id: max(1, len(variants_per_app.get(app_id) or [{}])) for app_id in include
    }
    total_rounds = max(variant_counts.values(), default=1)
    base = str(base_inventory_dir).rstrip("/")

    plan: list[tuple[int, str, dict[str, int]]] = []
    for round_index in range(total_rounds):
        round_variants = {
            app_id: round_index if round_index < count else 0
            for app_id, count in variant_counts.items()
        }
        inv_dir = f"{base}-{round_index}" if total_rounds > 1 else base
        plan.append((round_index, inv_dir, round_variants))
    return plan


def build_dev_inventory_matrix(
    compose: Compose,
    *,
    base_inventory_dir: str,
    include: Sequence[str],
    storage_constrained: bool,
    runtime: str,
    extra_vars: Mapping[str, Any] | None = None,
    services_disabled: str = "",
) -> list[tuple[int, str, dict[str, int]]]:
    """Build every folder in the matrix plan and return that plan so the
    caller can iterate it (typically by handing each folder to the deploy
    stage in turn)."""
    plan = plan_dev_inventory_matrix(
        roles_dir=str(compose.repo_root / "roles"),
        include=include,
        base_inventory_dir=base_inventory_dir,
    )
    for _round_index, inv_dir, round_variants in plan:
        spec = DevInventorySpec(
            inventory_dir=inv_dir,
            include=tuple(include),
            storage_constrained=storage_constrained,
            runtime=runtime,
            extra_vars=extra_vars,
            services_disabled=services_disabled,
            active_variants=round_variants,
        )
        build_dev_inventory(compose, spec)
    return plan


def _ensure_vault_password_file(compose: Compose, *, inventory_dir: str) -> None:
    inv_root = str(inventory_dir).rstrip("/")
    pw_file = f"{inv_root}/.password"
    compose.exec(
        [
            "sh",
            "-lc",
            f"mkdir -p {inv_root} && "
            f"[ -f {pw_file} ] || "
            f"printf '%s\n' 'ci-vault-password' > {pw_file}",
        ],
        check=True,
    )
