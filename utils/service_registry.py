from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Dict, List

import yaml

from utils.entity_name_utils import get_entity_name
from utils.invokable import types_from_group_names


class ServiceRegistryError(ValueError):
    """Raised when role-local service discovery is invalid."""


def _as_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalized_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def detect_service_channel(role_name: str) -> str:
    return "frontend" if role_name.startswith(("web-app-", "web-svc-")) else "backend"


def detect_deploy_type(role_name: str) -> str:
    detected = types_from_group_names([role_name])
    if "server" in detected:
        return "server"
    if "workstation" in detected:
        return "workstation"
    if "universal" in detected:
        return "universal"
    return "server" if role_name.startswith(("web-app-", "web-svc-")) else "universal"


def detect_service_bucket(role_name: str) -> str:
    deploy_type = detect_deploy_type(role_name)
    if deploy_type == "universal":
        return "universal"
    if deploy_type == "workstation":
        return "workstation"
    if role_name.startswith("web-svc-"):
        return "web-svc"
    if role_name.startswith("web-app-"):
        return "web-app"
    return deploy_type


def read_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return _as_mapping(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def load_applications_from_roles_dir(roles_dir: Path) -> Dict[str, Dict[str, Any]]:
    applications: Dict[str, Dict[str, Any]] = {}
    for role_dir in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        vars_file = role_dir / "vars" / "main.yml"
        if not vars_file.is_file():
            continue
        vars_data = read_yaml_file(vars_file)
        application_id = _normalized_name(vars_data.get("application_id"))
        if not application_id:
            continue
        applications[application_id] = read_yaml_file(role_dir / "config" / "main.yml")
    return applications


def discover_role_services(
    role_name: str,
    config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    services = _as_mapping(_as_mapping(config.get("compose")).get("services"))
    entity_name = get_entity_name(role_name)
    primary_entry = _as_mapping(services.get(entity_name))
    alias_entries = {
        key: _as_mapping(entry)
        for key, entry in services.items()
        if isinstance(entry, dict)
        and _normalized_name(_as_mapping(entry).get("canonical")) in {entity_name}
    }
    provides = _normalized_name(primary_entry.get("provides"))
    if provides == entity_name:
        provides = ""

    is_provider = bool(primary_entry) and (
        "shared" in primary_entry or "provides" in primary_entry or alias_entries
    )
    if not is_provider:
        return {}

    primary_id = provides or entity_name
    base_entry = {
        "role": role_name,
        "entity_name": entity_name,
        "source_key": entity_name,
        "deploy_type": detect_deploy_type(role_name),
        "bucket": detect_service_bucket(role_name),
        "service_type": detect_service_channel(role_name),
        "shared": bool(primary_entry.get("shared", False)),
        "enabled": bool(primary_entry.get("enabled", False)),
    }
    if provides:
        base_entry["provides"] = provides

    discovered: Dict[str, Dict[str, Any]] = {primary_id: base_entry}
    for alias_key, alias_entry in sorted(alias_entries.items()):
        discovered[alias_key] = {
            **base_entry,
            "source_key": alias_key,
            "canonical": primary_id,
            "shared": bool(alias_entry.get("shared", False)),
            "enabled": bool(alias_entry.get("enabled", False)),
        }

    return discovered


def build_service_registry_from_applications(
    applications: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    registry: Dict[str, Dict[str, Any]] = {}
    for role_name, config in sorted(applications.items()):
        role_services = discover_role_services(role_name, _as_mapping(config))
        for service_key, entry in role_services.items():
            existing = registry.get(service_key)
            if existing and existing.get("role") != entry.get("role"):
                raise ServiceRegistryError(
                    f"Duplicate service key '{service_key}' is declared by both "
                    f"'{existing.get('role')}' and '{entry.get('role')}'."
                )
            registry[service_key] = entry
    return registry


def build_service_registry_from_roles_dir(
    roles_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    return build_service_registry_from_applications(
        load_applications_from_roles_dir(roles_dir)
    )


def build_role_to_primary_service_key(
    service_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for service_key, entry in service_registry.items():
        if "canonical" in entry:
            continue
        role_name = _normalized_name(entry.get("role"))
        if role_name:
            result[role_name] = service_key
    return result


def canonical_service_key(
    service_registry: Dict[str, Dict[str, Any]],
    service_key: str,
) -> str:
    entry = _as_mapping(service_registry.get(service_key))
    return _normalized_name(entry.get("canonical")) or service_key


def equivalent_service_keys(
    service_registry: Dict[str, Dict[str, Any]],
    service_key: str,
) -> List[str]:
    primary = canonical_service_key(service_registry, service_key)
    keys = [
        key
        for key, entry in service_registry.items()
        if canonical_service_key(service_registry, key) == primary
    ]
    return sorted(keys)


def resolve_service_dependency_roles_from_config(
    config: Dict[str, Any],
    service_registry: Dict[str, Dict[str, Any]],
) -> List[str]:
    services = _as_mapping(_as_mapping(config.get("compose")).get("services"))
    includes: List[str] = []
    for service_key, service_conf in services.items():
        service_conf = _as_mapping(service_conf)
        if not (
            service_conf.get("enabled") is True and service_conf.get("shared") is True
        ):
            continue

        entry = _as_mapping(service_registry.get(service_key))
        role_name = _normalized_name(entry.get("role"))
        if role_name:
            includes.append(role_name)

    seen = set()
    ordered: List[str] = []
    for role_name in includes:
        if role_name not in seen:
            ordered.append(role_name)
            seen.add(role_name)
    return ordered


def load_run_after_from_roles_dir(roles_dir: Path, role_name: str) -> List[str]:
    meta = read_yaml_file(roles_dir / role_name / "meta" / "main.yml")
    galaxy_info = _as_mapping(meta.get("galaxy_info"))
    raw = galaxy_info.get("run_after") or []
    if not isinstance(raw, list):
        raise ServiceRegistryError(
            f"Invalid run_after in roles/{role_name}/meta/main.yml: expected list."
        )
    result: List[str] = []
    for item in raw:
        dep = _normalized_name(item)
        if not dep:
            raise ServiceRegistryError(
                f"Invalid run_after entry in roles/{role_name}/meta/main.yml: {item!r}"
            )
        result.append(dep)
    return result


_BUCKET_ORDER = {
    "universal": 0,
    "workstation": 1,
    "server": 2,
    "web-svc": 3,
    "web-app": 4,
}


def ordered_primary_service_entries(
    service_registry: Dict[str, Dict[str, Any]],
    roles_dir: Path,
) -> List[Dict[str, Any]]:
    primary_entries = {
        entry["role"]: {"id": service_key, **entry}
        for service_key, entry in service_registry.items()
        if "canonical" not in entry
    }

    ordered: List[Dict[str, Any]] = []
    for bucket in ("universal", "workstation", "server", "web-svc", "web-app"):
        roles_in_bucket = sorted(
            role_name
            for role_name, entry in primary_entries.items()
            if entry.get("bucket") == bucket
        )
        if not roles_in_bucket:
            continue

        graph: Dict[str, List[str]] = {role_name: [] for role_name in roles_in_bucket}
        indegree: Dict[str, int] = {role_name: 0 for role_name in roles_in_bucket}

        for role_name in roles_in_bucket:
            current = primary_entries[role_name]
            current_deploy_type = _normalized_name(current.get("deploy_type"))
            current_bucket_order = _BUCKET_ORDER[bucket]

            for dep_role in load_run_after_from_roles_dir(roles_dir, role_name):
                dep_deploy_type = detect_deploy_type(dep_role)
                if dep_deploy_type != current_deploy_type:
                    raise ServiceRegistryError(
                        f"{role_name}: run_after '{dep_role}' crosses deploy types "
                        f"({current_deploy_type} -> {dep_deploy_type})."
                    )

                dep_bucket = detect_service_bucket(dep_role)
                dep_bucket_order = _BUCKET_ORDER.get(dep_bucket, current_bucket_order)
                if dep_bucket_order > current_bucket_order:
                    raise ServiceRegistryError(
                        f"{role_name}: run_after '{dep_role}' points to a later loader "
                        f"bucket ({dep_bucket}), which cannot be satisfied."
                    )
                if dep_bucket_order < current_bucket_order:
                    continue
                if dep_role not in primary_entries:
                    raise ServiceRegistryError(
                        f"{role_name}: run_after '{dep_role}' is not a discovered "
                        "shared service role."
                    )

                graph[dep_role].append(role_name)
                indegree[role_name] += 1

        ready = deque(sorted(role for role, count in indegree.items() if count == 0))
        emitted = 0
        while ready:
            role_name = ready.popleft()
            ordered.append(primary_entries[role_name])
            emitted += 1

            for dependent in sorted(graph[role_name]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)

        if emitted != len(roles_in_bucket):
            raise ServiceRegistryError(
                f"Circular run_after dependency detected in bucket '{bucket}'."
            )

    return ordered
