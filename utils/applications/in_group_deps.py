from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import yaml

MetaDepsResolver = Callable[[str, str], list[str]]


def load_service_registry(project_root: str) -> dict[str, Any]:
    path = os.path.join(project_root, "group_vars", "all", "20_services.yml")
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except Exception:
        return {}

    registry = data.get("SERVICE_REGISTRY", {})
    return registry if isinstance(registry, dict) else {}


def meta_deps_from_disk(role: str, roles_dir: str) -> list[str]:
    meta_file = os.path.join(roles_dir, role, "meta", "main.yml")
    if not os.path.isfile(meta_file):
        return []

    try:
        with open(meta_file, encoding="utf-8") as handle:
            meta = yaml.safe_load(handle) or {}
    except Exception:
        return []

    deps: list[str] = []
    for dep in meta.get("dependencies", []):
        if isinstance(dep, str):
            deps.append(dep)
        elif isinstance(dep, dict):
            name = dep.get("role") or dep.get("name")
            if name:
                deps.append(name)
    return deps


def _resolve_service_role(
    service_key: str,
    service_conf: dict[str, Any],
    service_registry: dict[str, Any],
) -> str | None:
    entry = service_registry.get(service_key)
    if not isinstance(entry, dict):
        return None

    role = entry.get("role")
    if isinstance(role, str) and role:
        return role

    role_template = entry.get("role_template")
    if not isinstance(role_template, str) or not role_template:
        return None

    svc_type = service_conf.get("type", "")
    if not isinstance(svc_type, str) or not svc_type:
        return None

    return role_template.replace("{type}", svc_type)


def _service_dep_roles(
    role: str,
    applications: dict[str, Any],
    service_registry: dict[str, Any],
) -> list[str]:
    app_conf = applications.get(role) or {}
    services = app_conf.get("compose", {}).get("services", {})
    if not isinstance(services, dict):
        return []

    roles: list[str] = []
    for service_key, service_conf in services.items():
        if not isinstance(service_conf, dict):
            continue
        if not service_conf.get("enabled") or not service_conf.get("shared"):
            continue

        dep_role = _resolve_service_role(service_key, service_conf, service_registry)
        if dep_role and dep_role != role:
            roles.append(dep_role)
    return roles


def _collect_reachable_roles(
    role: str,
    applications: dict[str, Any],
    service_registry: dict[str, Any],
    roles_dir: str,
    seen: set[str],
    meta_deps_resolver: MetaDepsResolver,
) -> None:
    if role in seen:
        return
    seen.add(role)

    for dep in meta_deps_resolver(role, roles_dir):
        _collect_reachable_roles(
            dep,
            applications,
            service_registry,
            roles_dir,
            seen,
            meta_deps_resolver,
        )

    for dep_role in _service_dep_roles(role, applications, service_registry):
        _collect_reachable_roles(
            dep_role,
            applications,
            service_registry,
            roles_dir,
            seen,
            meta_deps_resolver,
        )


def applications_if_group_and_all_deps(
    applications: dict[str, Any],
    group_names: list[str],
    *,
    project_root: str | None = None,
    roles_dir: str | None = None,
    service_registry: dict[str, Any] | None = None,
    meta_deps_resolver: MetaDepsResolver | None = None,
) -> dict[str, Any]:
    if not isinstance(applications, dict):
        raise ValueError("'applications' must be a mapping")
    if not isinstance(group_names, list):
        raise ValueError("'group_names' must be a list")
    if not project_root and not roles_dir:
        raise ValueError("'project_root' or 'roles_dir' must be provided")

    if roles_dir is None:
        roles_dir = os.path.join(project_root, "roles")

    if service_registry is None:
        if project_root is None:
            raise ValueError(
                "'project_root' is required when 'service_registry' is not provided"
            )
        service_registry = load_service_registry(project_root)
    elif not isinstance(service_registry, dict):
        raise ValueError("'service_registry' must be a mapping")

    meta_deps_resolver = meta_deps_resolver or meta_deps_from_disk

    included: set[str] = set()
    for group in group_names:
        _collect_reachable_roles(
            group,
            applications,
            service_registry,
            roles_dir,
            included,
            meta_deps_resolver,
        )

    return {
        key: cfg
        for key, cfg in applications.items()
        if key in group_names or key in included
    }
