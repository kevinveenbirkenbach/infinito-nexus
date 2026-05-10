#!/usr/bin/env python3
"""Score every application role by the size of its transitive shared-service dependency closure."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from utils import PROJECT_ROOT
from utils.cache.yaml import load_yaml_any
from utils.roles.applications.services.registry import (
    build_service_registry_from_roles_dir,
    is_explicit_truth,
)
from utils.roles.mapping import ROLE_FILE_META_SERVICES, ROLE_FILE_VARS_MAIN

if TYPE_CHECKING:
    from pathlib import Path

TruthFn = Callable[[Any], bool]


def _strict_truth(value: Any) -> bool:
    """Like ``is_explicit_truth`` but rejects the ``'<X>' in group_names``
    Jinja form, so only literal ``True`` flags count as deps."""
    return value is True


def _truth_predicate(*, include_group_names: bool) -> TruthFn:
    return is_explicit_truth if include_group_names else _strict_truth


def _is_application_role(role_dir: Path) -> bool:
    vars_file = role_dir / ROLE_FILE_VARS_MAIN
    if not vars_file.is_file():
        return False
    data = load_yaml_any(str(vars_file), default_if_missing={}) or {}
    if not isinstance(data, dict):
        return False
    application_id = data.get("application_id")
    return isinstance(application_id, str) and bool(application_id.strip())


def _load_role_services(role_dir: Path) -> dict[str, Any]:
    services_path = role_dir / ROLE_FILE_META_SERVICES
    if not services_path.is_file():
        return {}
    data = load_yaml_any(str(services_path), default_if_missing={}) or {}
    return data if isinstance(data, dict) else {}


def _direct_service_dep_roles(
    services_map: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    *,
    truth: TruthFn,
) -> list[str]:
    raw: list[str] = []
    for service_key, entry in services_map.items():
        if not isinstance(entry, dict):
            continue
        if not (truth(entry.get("enabled")) and truth(entry.get("shared"))):
            continue
        registry_entry = registry.get(service_key)
        if not isinstance(registry_entry, dict):
            continue
        provider = registry_entry.get("role")
        if isinstance(provider, str) and provider.strip():
            raw.append(provider.strip())

    seen: set[str] = set()
    deduped: list[str] = []
    for role_name in raw:
        if role_name not in seen:
            seen.add(role_name)
            deduped.append(role_name)
    return deduped


def _resolve_transitively(
    start_role: str,
    forward_graph: dict[str, list[str]],
    *,
    max_level: int | None = None,
) -> list[str]:
    """BFS over an adjacency map. ``max_level`` caps recursion depth:
    ``1`` returns direct neighbours only, ``2`` adds their direct
    neighbours, etc. ``None`` walks the full closure. The start role
    itself is never included in the result.
    """
    seen: set[str] = {start_role}
    order: list[str] = []
    queue: list[tuple[str, int]] = [
        (role_name, 1) for role_name in forward_graph.get(start_role, [])
    ]

    while queue:
        role_name, depth = queue.pop(0)
        if role_name in seen:
            continue
        seen.add(role_name)
        order.append(role_name)
        if max_level is not None and depth >= max_level:
            continue
        next_depth = depth + 1
        queue.extend(
            (next_role, next_depth)
            for next_role in forward_graph.get(role_name, [])
            if next_role not in seen
        )
    return order


def _build_direct_graphs(
    roles_dir: Path,
    registry: dict[str, dict[str, Any]],
    *,
    truth: TruthFn,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return ``(forward, reverse)`` adjacency maps over all role dirs.

    ``forward[A]`` is the list of provider roles that ``A`` directly
    depends on (services it embeds). ``reverse[B]`` is the list of
    roles that directly depend on ``B`` (consumers that embed ``B``).
    """
    forward: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = {}
    for role_dir in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        consumer = role_dir.name
        services_map = _load_role_services(role_dir)
        providers = _direct_service_dep_roles(services_map, registry, truth=truth)
        forward[consumer] = providers
        for provider in providers:
            reverse.setdefault(provider, []).append(consumer)
    return forward, reverse


def compute_complexity_rows(
    roles_dir: Path,
    *,
    include_group_names: bool = True,
    max_level: int | None = None,
) -> list[tuple[str, int, list[str], int, list[str]]]:
    """Return ``(role, embeds, services, consumers, consumed_by)`` per
    application role.

    ``embeds`` / ``services`` count and list the provider roles the
    application transitively embeds (forward closure). ``consumers`` /
    ``consumed_by`` count and list the application roles that
    transitively embed *this* role (reverse closure). Both directions
    share the same BFS depth cap ``max_level`` (``None`` = unbounded).
    The role itself is never counted in either direction.
    """
    registry = build_service_registry_from_roles_dir(roles_dir)
    truth = _truth_predicate(include_group_names=include_group_names)
    forward, reverse = _build_direct_graphs(roles_dir, registry, truth=truth)

    rows: list[tuple[str, int, list[str], int, list[str]]] = []
    for role_dir in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        if not _is_application_role(role_dir):
            continue
        services = _resolve_transitively(role_dir.name, forward, max_level=max_level)
        consumers = _resolve_transitively(role_dir.name, reverse, max_level=max_level)
        rows.append((role_dir.name, len(services), services, len(consumers), consumers))
    return rows


def _render_table(rows: list[tuple[str, int, list[str], int, list[str]]]) -> str:
    """Render counts only (no name lists). Use ``--format json`` for the
    full role names."""
    if not rows:
        return ""
    name_w = max(len("name"), max(len(r[0]) for r in rows))
    out_w = max(len("embeds"), max(len(str(r[1])) for r in rows))
    in_w = max(len("consumers"), max(len(str(r[3])) for r in rows))
    lines = [
        f"{'name':<{name_w}}  {'embeds':>{out_w}}  {'consumers':>{in_w}}",
        f"{'-' * name_w}  {'-' * out_w}  {'-' * in_w}",
    ]
    for name, embeds, _services, consumers, _consumed_by in rows:
        lines.append(f"{name:<{name_w}}  {embeds:>{out_w}}  {consumers:>{in_w}}")
    return "\n".join(lines)


def _render_json(rows: list[tuple[str, int, list[str], int, list[str]]]) -> str:
    import json as _json

    payload = [
        {
            "name": name,
            "embeds": embeds,
            "services": services,
            "consumers": consumers,
            "consumed_by": consumed_by,
        }
        for name, embeds, services, consumers, consumed_by in rows
    ]
    return _json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="infinito meta roles applications complexity",
        description=(
            "For every application role, list its transitively resolved "
            "shared-service dependencies and the resulting complexity score."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--sort",
        choices=("embeds", "name", "consumers"),
        default="embeds",
        help=(
            "Sort by 'embeds' (ascending, default — service deps the role "
            "embeds), 'consumers' (ascending — roles that embed this one), "
            "or 'name' (ascending)."
        ),
    )
    p.add_argument(
        "--no-group-names",
        action="store_true",
        help=(
            "Ignore services whose enabled/shared flag is the "
            "'<role>' in group_names Jinja form. Only literal `true` "
            "flags count as deps."
        ),
    )
    p.add_argument(
        "--format",
        choices=("cli", "json"),
        default="cli",
        help=(
            "Output format. 'cli' (default) shows counts only — name, "
            "embeds, consumers — for a compact terminal view. 'json' "
            "emits the full payload including the resolved service and "
            "consumer role lists."
        ),
    )
    p.add_argument(
        "-L",
        "--level",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Limit recursion depth: 1 = direct deps only, 2 = direct + "
            "their direct, ... Default: unbounded (full closure)."
        ),
    )
    args = p.parse_args(argv)

    if args.level is not None and args.level < 1:
        p.error("--level/-L must be >= 1")

    roles_dir = PROJECT_ROOT / "roles"
    if not roles_dir.is_dir():
        print(f"Error: roles directory not found: {roles_dir}", file=sys.stderr)
        return 1

    rows = compute_complexity_rows(
        roles_dir,
        include_group_names=not args.no_group_names,
        max_level=args.level,
    )

    if args.sort == "embeds":
        rows.sort(key=lambda r: (r[1], r[0]))
    elif args.sort == "consumers":
        rows.sort(key=lambda r: (r[3], r[0]))
    else:
        rows.sort(key=lambda r: r[0])

    rendered = _render_json(rows) if args.format == "json" else _render_table(rows)
    if rendered:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
