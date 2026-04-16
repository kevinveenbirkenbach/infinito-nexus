from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from utils.service_registry import (
    build_service_registry_from_roles_dir,
    canonical_service_key,
    equivalent_service_keys,
)


class ServicesDisabledConflictError(RuntimeError):
    """Raised when SERVICES_DISABLED conflicts with an existing inventory."""


def parse_services_disabled(env_value: str) -> list[str]:
    """Parse a space- or comma-separated list of service names."""
    return [s.strip() for s in env_value.replace(",", " ").split() if s.strip()]


def find_roles_with_service(service_name: str, roles_dir: Path) -> set[str]:
    """
    Return all role IDs whose config/main.yml defines the given service under
    compose.services (regardless of whether an image is set).
    """
    role_ids: set[str] = set()
    if not roles_dir.exists():
        return role_ids

    for role_dir in sorted(roles_dir.iterdir()):
        if not role_dir.is_dir():
            continue
        config_file = role_dir / "config" / "main.yml"
        if not config_file.exists():
            continue
        try:
            with config_file.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            continue
        compose_services = (config.get("compose") or {}).get("services") or {}
        if service_name in compose_services:
            role_ids.add(role_dir.name)

    return role_ids


def find_provider_roles(services: list[str], roles_dir: Path) -> dict[str, str]:
    """
    Scan all role configs and return a mapping of service_name -> application_id
    for roles that directly provide the service (i.e., have an image defined for it).
    The application_id equals the role folder name.
    """
    mapping: dict[str, str] = {}
    if not roles_dir.exists():
        return mapping

    for role_dir in sorted(roles_dir.iterdir()):
        if not role_dir.is_dir():
            continue
        config_file = role_dir / "config" / "main.yml"
        if not config_file.exists():
            continue
        try:
            with config_file.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            continue

        compose_services = (config.get("compose") or {}).get("services") or {}
        for svc_name, svc_config in compose_services.items():
            if (
                svc_name in services
                and isinstance(svc_config, dict)
                and "image" in svc_config
            ):
                mapping[svc_name] = role_dir.name

    return mapping


def remove_roles_from_inventory(
    inventory_file: Path, application_ids: list[str]
) -> None:
    """Remove the given application_ids from the inventory devices.yml."""
    if not inventory_file.exists() or not application_ids:
        return

    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    with inventory_file.open("r", encoding="utf-8") as f:
        doc = yaml_rt.load(f)

    if not isinstance(doc, CommentedMap):
        return

    all_section = doc.get("all")
    if not isinstance(all_section, CommentedMap):
        return

    children = all_section.get("children")
    if not isinstance(children, CommentedMap):
        return

    changed = False
    for app_id in application_ids:
        if app_id in children:
            del children[app_id]
            changed = True
            print(f"[INFO] SERVICES_DISABLED: removed '{app_id}' from inventory")
        else:
            print(
                f"[INFO] SERVICES_DISABLED: '{app_id}' not found in inventory — skipping"
            )

    if changed:
        with inventory_file.open("w", encoding="utf-8") as f:
            yaml_rt.dump(doc, f)


def apply_services_disabled(
    host_vars_file: Path,
    services: list[str],
    roles_dir: Path,
    inventory_file: Optional[Path] = None,
) -> None:
    """
    For every role under roles_dir whose config/main.yml defines a service listed
    in `services`, set enabled: false and shared: false in host_vars_file under
    applications.<app_id>.compose.services.<svc_name>.  Missing application,
    compose, or services blocks are created as needed.

    If inventory_file is provided, also removes the provider role for each service
    from the inventory (devices.yml).
    """
    if not services:
        return

    # --- host_vars: disable services ---
    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    if not host_vars_file.exists():
        return

    with host_vars_file.open("r", encoding="utf-8") as f:
        doc = yaml_rt.load(f)

    if not isinstance(doc, CommentedMap):
        return

    applications = doc.get("applications")
    if not isinstance(applications, CommentedMap):
        return

    changed = False
    for svc_name in services:
        for app_id in sorted(find_roles_with_service(svc_name, roles_dir)):
            app_data = applications.get(app_id)
            if not isinstance(app_data, CommentedMap):
                app_data = CommentedMap()
                applications[app_id] = app_data

            compose = app_data.get("compose")
            if not isinstance(compose, CommentedMap):
                compose = CommentedMap()
                app_data["compose"] = compose

            svc_map = compose.get("services")
            if not isinstance(svc_map, CommentedMap):
                svc_map = CommentedMap()
                compose["services"] = svc_map

            svc = svc_map.get(svc_name)
            if not isinstance(svc, CommentedMap):
                svc = CommentedMap()
                svc_map[svc_name] = svc
            svc["enabled"] = False
            svc["shared"] = False
            changed = True
            print(
                f"[INFO] SERVICES_DISABLED: {app_id}.compose.services.{svc_name} "
                "→ enabled=false, shared=false"
            )

    if changed:
        with host_vars_file.open("w", encoding="utf-8") as f:
            yaml_rt.dump(doc, f)

    # --- inventory: remove provider roles ---
    if inventory_file is not None:
        provider_map = find_provider_roles(services, roles_dir)
        if provider_map:
            print(f"[INFO] SERVICES_DISABLED: provider roles found: {provider_map}")
            remove_roles_from_inventory(inventory_file, list(provider_map.values()))
        else:
            print(
                "[INFO] SERVICES_DISABLED: no provider roles found for given services"
            )


def apply_services_disabled_from_env(
    host_vars_file: Path,
    roles_dir: Path,
    inventory_file: Optional[Path] = None,
) -> None:
    """Read SERVICES_DISABLED from the environment and apply to host_vars and inventory."""
    raw = os.environ.get("SERVICES_DISABLED", "").strip()
    if not raw:
        return
    services = parse_services_disabled(raw)
    print(f"[INFO] SERVICES_DISABLED={raw!r} → disabling: {services}")
    apply_services_disabled(
        host_vars_file, services, roles_dir=roles_dir, inventory_file=inventory_file
    )


def _load_yaml_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _inventory_application_ids(inventory_file: Path) -> set[str]:
    doc = _load_yaml_mapping(inventory_file)
    all_section = doc.get("all") or {}
    children = all_section.get("children") or {}
    if not isinstance(children, dict):
        return set()
    return {app_id for app_id, value in children.items() if isinstance(value, dict)}


def find_services_disabled_conflicts(
    inventory_dir: Path,
    services: list[str],
    roles_dir: Path,
) -> list[str]:
    """
    Return human-readable conflicts when SERVICES_DISABLED disagrees with the
    existing inventory/host_vars state.
    """
    if not services:
        return []

    inventory_file = inventory_dir / "devices.yml"
    deployed_app_ids = _inventory_application_ids(inventory_file)
    host_vars_dir = inventory_dir / "host_vars"
    host_vars_files = (
        sorted(host_vars_dir.glob("*.yml")) if host_vars_dir.is_dir() else []
    )
    service_registry = build_service_registry_from_roles_dir(roles_dir)

    conflicts: list[str] = []
    for service in services:
        primary_service = (
            canonical_service_key(service_registry, service)
            if service in service_registry
            else service
        )
        equivalent_keys = (
            equivalent_service_keys(service_registry, primary_service)
            if primary_service in service_registry
            else [service]
        )
        provider_role = (service_registry.get(primary_service) or {}).get("role")
        if isinstance(provider_role, str) and provider_role in deployed_app_ids:
            conflicts.append(
                f"service '{service}' is disabled, but provider role "
                f"'{provider_role}' is still active in {inventory_file}"
            )

        for host_vars_file in host_vars_files:
            doc = _load_yaml_mapping(host_vars_file)
            applications = doc.get("applications") or {}
            if not isinstance(applications, dict):
                continue
            for app_id in sorted(deployed_app_ids):
                app_conf = applications.get(app_id) or {}
                compose = app_conf.get("compose") or {}
                service_map = compose.get("services") or {}
                if not isinstance(service_map, dict):
                    continue
                for service_key in equivalent_keys:
                    service_conf = service_map.get(service_key) or {}
                    if not isinstance(service_conf, dict):
                        continue
                    enabled = bool(service_conf.get("enabled", False))
                    shared = bool(service_conf.get("shared", False))
                    if enabled or shared:
                        conflicts.append(
                            f"service '{service}' is disabled, but "
                            f"{host_vars_file}:{app_id}.compose.services.{service_key} "
                            f"still has enabled={enabled}, shared={shared}"
                        )

    return conflicts


def assert_services_disabled_inventory_consistency_from_env(
    inventory_dir: Path,
    roles_dir: Path,
) -> None:
    """Fail fast when SERVICES_DISABLED conflicts with the existing inventory."""
    raw = os.environ.get("SERVICES_DISABLED", "").strip()
    if not raw:
        return

    services = parse_services_disabled(raw)
    conflicts = find_services_disabled_conflicts(
        inventory_dir=inventory_dir,
        services=services,
        roles_dir=roles_dir,
    )
    if not conflicts:
        return

    details = "\n  - ".join(conflicts)
    raise ServicesDisabledConflictError(
        "SERVICES_DISABLED conflicts with the current inventory state.\n"
        f"SERVICES_DISABLED={raw!r}\n"
        "Conflicts:\n"
        f"  - {details}\n"
        "Recreate or clean the inventory, or remove the conflicting service from "
        "SERVICES_DISABLED."
    )
