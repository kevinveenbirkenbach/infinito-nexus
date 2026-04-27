#!/usr/bin/env python3
"""One-shot migration script for requirements 008 + 009 + 010.

Run from the repo root: `python3 tasks/utils/migrate_meta_layout.py`.

Idempotent: re-running on an already-migrated tree is a no-op for that role.
"""

from __future__ import annotations

import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES_DIR = REPO_ROOT / "roles"
NETWORKS_FILE = REPO_ROOT / "group_vars" / "all" / "08_networks.yml"
PORTS_FILE = REPO_ROOT / "group_vars" / "all" / "09_ports.yml"


sys.path.insert(0, str(REPO_ROOT))
from utils.entity_name_utils import get_entity_name  # noqa: E402


ALLOWED_LIFECYCLES = {
    "planned",
    "pre-alpha",
    "alpha",
    "beta",
    "stable",
    "deprecated",
}


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    return yaml.safe_load(text)


def _dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        data = {}
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )
    path.write_text(text, encoding="utf-8")


def _ordered_dump(data: Any) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def _empty_dir(path: Path) -> None:
    if not path.is_dir():
        return
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
    path.rmdir()


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged: Dict[str, Any] = {}
        for key, value in base.items():
            merged[key] = value
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return override


def _detect_credential_collision(
    schema_creds: Dict[str, Any],
    config_creds: Dict[str, Any],
    role_name: str,
) -> None:
    """Walk both trees and fail loudly on shared paths."""

    def _walk(prefix: str, schema_node: Any, config_node: Any) -> None:
        if not isinstance(schema_node, dict) or not isinstance(config_node, dict):
            if prefix:
                raise SystemExit(
                    f"{role_name}: credential key collision at "
                    f"credentials.{prefix}: defined in both schema/main.yml and "
                    f"config/main.yml.credentials"
                )
            return
        for key, schema_child in schema_node.items():
            if key in config_node:
                next_prefix = f"{prefix}.{key}" if prefix else key
                config_child = config_node[key]
                if isinstance(schema_child, dict) and isinstance(config_child, dict):
                    is_schema_leaf = (
                        "description" in schema_child
                        or "algorithm" in schema_child
                        or "validation" in schema_child
                        or "default" in schema_child
                    )
                    if is_schema_leaf:
                        raise SystemExit(
                            f"{role_name}: credential key collision at "
                            f"credentials.{next_prefix}: present in both "
                            f"schema/main.yml and config/main.yml.credentials"
                        )
                    _walk(next_prefix, schema_child, config_child)
                else:
                    raise SystemExit(
                        f"{role_name}: credential key collision at "
                        f"credentials.{next_prefix}: present in both "
                        f"schema/main.yml and config/main.yml.credentials"
                    )

    _walk("", schema_creds, config_creds)


def _convert_runtime_creds_to_schema(node: Any) -> Any:
    """Recursively turn `key: '{{ jinja }}'` runtime credentials into schema entries.

    Each leaf becomes ``{description, algorithm: plain, default: <jinja>}``.
    Nested dicts are walked.
    """
    if not isinstance(node, dict):
        return node

    converted: Dict[str, Any] = {}
    for key, value in node.items():
        if isinstance(value, dict):
            looks_like_schema = any(
                inner_key in value
                for inner_key in ("description", "algorithm", "validation", "default")
            )
            if looks_like_schema:
                if "algorithm" not in value:
                    value = {"algorithm": "plain", **value}
                converted[key] = value
            else:
                converted[key] = _convert_runtime_creds_to_schema(value)
        elif isinstance(value, str):
            converted[key] = {
                "description": (
                    f"Runtime credential value imported from config/main.yml "
                    f"for '{key}'."
                ),
                "algorithm": "plain",
                "default": value,
            }
        else:
            converted[key] = {
                "description": (
                    f"Runtime credential value imported from config/main.yml "
                    f"for '{key}'."
                ),
                "algorithm": "plain",
                "default": value,
            }
    return converted


def _build_meta_files_for_role(
    role_dir: Path,
    networks_for_role: Optional[Dict[str, Any]],
    ports_for_role: Dict[str, Dict[str, Any]],
    relays_for_role: Dict[str, Dict[str, int]],
) -> None:
    """Run the file-move + content-rewrite for a single role.

    Side effects (in `role_dir`):
      * Reads ``schema/main.yml``, ``users/main.yml``, ``config/main.yml`` and
        ``meta/main.yml`` if present.
      * Writes ``meta/{schema,users,server,rbac,services,volumes}.yml``
        as required.
      * Strips ``run_after`` and ``lifecycle`` from ``meta/main.yml`` and
        re-emits it.
      * Removes ``schema/``, ``users/``, ``config/`` directories on success.
    """
    role_name = role_dir.name
    primary_entity = get_entity_name(role_name) or role_name

    config = _load_yaml(role_dir / "config" / "main.yml") or {}
    schema = _load_yaml(role_dir / "schema" / "main.yml") or {}
    users_data = _load_yaml(role_dir / "users" / "main.yml") or {}
    meta_main = _load_yaml(role_dir / "meta" / "main.yml") or {}

    if not isinstance(config, dict):
        raise SystemExit(f"{role_name}: config/main.yml is not a mapping")
    if not isinstance(schema, dict):
        raise SystemExit(f"{role_name}: schema/main.yml is not a mapping")
    if not isinstance(users_data, dict):
        raise SystemExit(f"{role_name}: users/main.yml is not a mapping")
    if not isinstance(meta_main, dict):
        raise SystemExit(f"{role_name}: meta/main.yml is not a mapping")

    # ---- credentials merge --------------------------------------------------
    schema_creds = (
        dict(schema.get("credentials") or {})
        if isinstance(schema.get("credentials"), dict)
        else {}
    )
    config_creds_raw = config.get("credentials") if isinstance(config, dict) else None
    config_creds = dict(config_creds_raw) if isinstance(config_creds_raw, dict) else {}
    converted_config_creds = _convert_runtime_creds_to_schema(config_creds)
    _detect_credential_collision(schema_creds, converted_config_creds, role_name)

    merged_creds = _deep_merge(schema_creds, converted_config_creds)

    if merged_creds:
        _dump_yaml(
            role_dir / "meta" / "schema.yml",
            {"credentials": merged_creds},
        )

    # ---- users.yml ----------------------------------------------------------
    users_block = users_data.get("users") if isinstance(users_data, dict) else None
    if isinstance(users_block, dict) and users_block:
        _dump_yaml(role_dir / "meta" / "users.yml", users_block)

    # ---- server, rbac -------------------------------------------------------
    server_block = config.get("server")
    if isinstance(server_block, dict) and server_block:
        server_payload = dict(server_block)
        if networks_for_role:
            server_payload["networks"] = {"local": networks_for_role}
        _dump_yaml(role_dir / "meta" / "server.yml", server_payload)
    elif networks_for_role:
        _dump_yaml(
            role_dir / "meta" / "server.yml",
            {"networks": {"local": networks_for_role}},
        )

    rbac_block = config.get("rbac")
    if isinstance(rbac_block, dict) and rbac_block:
        _dump_yaml(role_dir / "meta" / "rbac.yml", rbac_block)

    # ---- compose volumes ----------------------------------------------------
    compose = config.get("compose") if isinstance(config, dict) else None
    compose = compose if isinstance(compose, dict) else {}
    volumes_block = compose.get("volumes")
    if isinstance(volumes_block, dict) and volumes_block:
        _dump_yaml(role_dir / "meta" / "volumes.yml", volumes_block)

    # ---- services + inlined keys + ports + run_after/lifecycle --------------
    compose_services_raw = compose.get("services")
    services: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    if isinstance(compose_services_raw, dict):
        for service_key, service_value in compose_services_raw.items():
            if isinstance(service_value, dict):
                # rename `port:` (int or quoted) -> `ports.inter`
                service_copy = dict(service_value)
                if "port" in service_copy:
                    raw_port = service_copy.pop("port")
                    try:
                        inter_port = int(str(raw_port).strip())
                    except (TypeError, ValueError):
                        # Non-int (Jinja expression for example) -> stay as
                        # `inter` but raw, keep semantics
                        inter_port = raw_port
                    ports_field = service_copy.get("ports")
                    if not isinstance(ports_field, dict):
                        ports_field = {}
                    ports_field["inter"] = inter_port
                    service_copy["ports"] = ports_field
                services[service_key] = service_copy
            else:
                services[service_key] = service_value

    # Inline top-level non-special keys under primary_entity
    EXCLUDED_TOP_LEVEL_KEYS = {"compose", "server", "rbac", "credentials"}
    inlined: Dict[str, Any] = {}
    for key, value in config.items():
        if key in EXCLUDED_TOP_LEVEL_KEYS:
            continue
        inlined[key] = value
    if inlined:
        primary_node = services.setdefault(primary_entity, {})
        if not isinstance(primary_node, dict):
            raise SystemExit(
                f"{role_name}: cannot inline keys under non-dict primary entity "
                f"'{primary_entity}'."
            )
        for key, value in inlined.items():
            if key in primary_node:
                # Preserve compose-defined values, layer inlined under them
                primary_node[key] = _deep_merge(value, primary_node[key])
            else:
                primary_node[key] = value
        services[primary_entity] = primary_node

    # Apply per-entity ports from 09_ports.yml
    for entity_key, ports_payload in ports_for_role.items():
        node = services.setdefault(entity_key, {})
        if not isinstance(node, dict):
            raise SystemExit(
                f"{role_name}: cannot attach ports to non-dict entity '{entity_key}'."
            )
        node_ports = node.get("ports") if isinstance(node.get("ports"), dict) else {}
        # ports_payload looks like {'local': {...}, 'public': {...}}
        for scope_name, scope_map in ports_payload.items():
            existing_scope = node_ports.get(scope_name)
            if isinstance(existing_scope, dict):
                merged_scope = dict(existing_scope)
                merged_scope.update(scope_map)
                node_ports[scope_name] = merged_scope
            else:
                node_ports[scope_name] = dict(scope_map)
        node["ports"] = node_ports
        services[entity_key] = node

    # Apply relay ranges
    for entity_key, relay in relays_for_role.items():
        node = services.setdefault(entity_key, {})
        if not isinstance(node, dict):
            raise SystemExit(
                f"{role_name}: cannot attach relay range to non-dict entity "
                f"'{entity_key}'."
            )
        node_ports = node.get("ports") if isinstance(node.get("ports"), dict) else {}
        public_scope = (
            node_ports.get("public")
            if isinstance(node_ports.get("public"), dict)
            else {}
        )
        public_scope["relay"] = {"start": relay["start"], "end": relay["end"]}
        node_ports["public"] = public_scope
        node["ports"] = node_ports
        services[entity_key] = node

    # Migrate run_after / lifecycle from meta/main.yml
    galaxy_info_changed = False
    galaxy_info = meta_main.get("galaxy_info")
    if isinstance(galaxy_info, dict):
        run_after_value = galaxy_info.pop("run_after", None)
        lifecycle_value = galaxy_info.pop("lifecycle", None)
        if run_after_value is not None or lifecycle_value is not None:
            galaxy_info_changed = True
        primary_node = services.setdefault(primary_entity, {})
        if not isinstance(primary_node, dict):
            raise SystemExit(
                f"{role_name}: cannot attach run_after/lifecycle to non-dict "
                f"primary entity '{primary_entity}'."
            )
        if isinstance(run_after_value, list) and run_after_value:
            primary_node["run_after"] = list(run_after_value)
        if isinstance(lifecycle_value, str) and lifecycle_value.strip():
            stripped = lifecycle_value.strip().lower()
            if stripped not in ALLOWED_LIFECYCLES:
                raise SystemExit(
                    f"{role_name}: meta/main.yml.galaxy_info.lifecycle has "
                    f"unknown value {lifecycle_value!r}. Allowed: "
                    f"{sorted(ALLOWED_LIFECYCLES)}."
                )
            primary_node["lifecycle"] = stripped
        services[primary_entity] = primary_node

    if services:
        _dump_yaml(role_dir / "meta" / "services.yml", dict(services))

    if galaxy_info_changed:
        _dump_yaml(role_dir / "meta" / "main.yml", meta_main)

    # ---- cleanup old directories -------------------------------------------
    for legacy in ("config", "schema", "users"):
        legacy_dir = role_dir / legacy
        if legacy_dir.is_dir():
            _empty_dir(legacy_dir)


# --------------------------------------------------------------------------
# Centralised network/port extraction
# --------------------------------------------------------------------------


def _build_network_index() -> Dict[str, Dict[str, Any]]:
    networks = _load_yaml(NETWORKS_FILE) or {}
    raw = networks.get("defaults_networks", {}) if isinstance(networks, dict) else {}
    local = raw.get("local", {}) if isinstance(raw, dict) else {}
    if not isinstance(local, dict):
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for role_name, value in local.items():
        if isinstance(value, str):
            result[role_name] = {"subnet": value}
        elif isinstance(value, dict):
            entry: Dict[str, Any] = {}
            if "subnet" in value:
                entry["subnet"] = value["subnet"]
            if "dns_resolver" in value:
                entry["dns_resolver"] = value["dns_resolver"]
            if entry:
                result[role_name] = entry
    return result


# Roles where multi-entity port keys use a non-default split. Empty by default;
# `split_role_entity` falls back to a deterministic suffix split rooted in the
# real role directory listing.
_KNOWN_ROLES_CACHE: Optional[Set[str]] = None


def _all_role_names() -> Set[str]:
    global _KNOWN_ROLES_CACHE
    if _KNOWN_ROLES_CACHE is None:
        _KNOWN_ROLES_CACHE = {
            child.name for child in ROLES_DIR.iterdir() if child.is_dir()
        }
    return _KNOWN_ROLES_CACHE


def _split_role_and_entity(combined_key: str) -> Tuple[str, Optional[str]]:
    """Return ``(role_name, entity_or_None)`` for a `09_ports.yml` key.

    The convention is ``<role>_<entity>`` for multi-entity roles, e.g.
    ``web-app-bluesky_api`` -> ``("web-app-bluesky", "api")``. Single-entity
    roles use the bare role name, e.g. ``web-app-gitea`` -> ``("web-app-gitea", None)``.
    Resolution is deterministic: if the bare key is itself a known role, no
    split is attempted; otherwise the suffix after the last ``_`` is treated
    as the entity name when the prefix matches a known role.
    """
    known = _all_role_names()
    if combined_key in known:
        return combined_key, None
    if "_" in combined_key:
        prefix, suffix = combined_key.rsplit("_", 1)
        if prefix in known:
            return prefix, suffix
    # Unknown role; carry the key through verbatim so the caller can flag it.
    return combined_key, None


def _build_port_index() -> Tuple[
    Dict[str, Dict[str, Dict[str, Any]]], Dict[str, Dict[str, Dict[str, int]]]
]:
    """Return ``(ports_for_role, relays_for_role)``.

    Shape::

        ports_for_role[role][entity] = {"local": {<cat>: <int>}, "public": {...}}
        relays_for_role[role][entity] = {"start": <int>, "end": <int>}
    """
    ports_doc = _load_yaml(PORTS_FILE) or {}
    ports_root = ports_doc.get("ports", {}) if isinstance(ports_doc, dict) else {}
    if not isinstance(ports_root, dict):
        return {}, {}

    ports_for_role: Dict[str, Dict[str, Dict[str, Any]]] = {}
    relays_for_role: Dict[str, Dict[str, Dict[str, int]]] = {}

    for scope in ("localhost", "public"):
        scope_block = ports_root.get(scope, {})
        if not isinstance(scope_block, dict):
            continue
        scope_label = "local" if scope == "localhost" else "public"
        for category, entries in scope_block.items():
            if category == "relay_port_ranges":
                if not isinstance(entries, dict):
                    continue
                for combined_key, port_value in entries.items():
                    if not isinstance(port_value, int):
                        continue
                    if combined_key.endswith("_start"):
                        base = combined_key[: -len("_start")]
                        kind = "start"
                    elif combined_key.endswith("_end"):
                        base = combined_key[: -len("_end")]
                        kind = "end"
                    else:
                        continue
                    role_name, entity = _split_role_and_entity(base)
                    entity_key = entity or get_entity_name(role_name) or role_name
                    role_relays = relays_for_role.setdefault(role_name, {})
                    relay_entry = role_relays.setdefault(entity_key, {})
                    relay_entry[kind] = port_value
                continue

            if not isinstance(entries, dict):
                continue

            for combined_key, port_value in entries.items():
                if not isinstance(port_value, int):
                    continue
                role_name, entity = _split_role_and_entity(combined_key)
                entity_key = entity or get_entity_name(role_name) or role_name
                role_ports = ports_for_role.setdefault(role_name, {})
                entity_ports = role_ports.setdefault(entity_key, {})
                scope_map = entity_ports.setdefault(scope_label, {})
                scope_map[category] = port_value

    return ports_for_role, relays_for_role


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main() -> int:
    if not ROLES_DIR.is_dir():
        print(f"roles directory not found at {ROLES_DIR}", file=sys.stderr)
        return 1

    networks = _build_network_index()
    ports_for_role, relays_for_role = _build_port_index()

    role_dirs = sorted(p for p in ROLES_DIR.iterdir() if p.is_dir())
    touched = 0
    for role_dir in role_dirs:
        legacy_dirs_present = any(
            (role_dir / sub).is_dir() for sub in ("config", "schema", "users")
        )
        meta_main_path = role_dir / "meta" / "main.yml"
        meta_main = _load_yaml(meta_main_path) if meta_main_path.is_file() else None
        gi = (
            meta_main.get("galaxy_info") if isinstance(meta_main, dict) else None
        ) or {}
        meta_main_carries_legacy = isinstance(gi, dict) and (
            "run_after" in gi or "lifecycle" in gi
        )
        has_centralised_data = (
            role_dir.name in networks
            or role_dir.name in ports_for_role
            or role_dir.name in relays_for_role
        )
        if not (
            legacy_dirs_present or meta_main_carries_legacy or has_centralised_data
        ):
            continue

        _build_meta_files_for_role(
            role_dir,
            networks.get(role_dir.name),
            ports_for_role.get(role_dir.name, {}),
            relays_for_role.get(role_dir.name, {}),
        )
        touched += 1

    print(f"migrated {touched} roles", file=sys.stderr)

    # Strip migrated keys from group_vars/all/{08_networks,09_ports}.yml.
    # 09_ports.yml is deleted entirely; 08_networks.yml keeps NETWORK_IPV6_ENABLED
    # plus defaults_networks.internet.
    networks_doc = _load_yaml(NETWORKS_FILE) or {}
    if isinstance(networks_doc, dict):
        defaults = networks_doc.get("defaults_networks")
        if isinstance(defaults, dict) and "local" in defaults:
            defaults.pop("local", None)
            if not defaults:
                networks_doc.pop("defaults_networks", None)
            else:
                networks_doc["defaults_networks"] = defaults
        # Inject PORT_BANDS map (per req-009).
        networks_doc["PORT_BANDS"] = {
            "local": {
                "http": {"start": 8001, "end": 8099},
                "websocket": {"start": 4001, "end": 4099},
                "oauth2": {"start": 16480, "end": 16499},
                "database": {"start": 3306, "end": 5432},
                "ldap": {"start": 389, "end": 389},
            },
            "public": {
                "ssh": {"start": 2201, "end": 2299},
                "stun_turn": {"start": 3478, "end": 3499},
                "stun_turn_tls": {"start": 5349, "end": 5399},
                "federation": {"start": 8448, "end": 8499},
                "ldaps": {"start": 636, "end": 636},
                "relay": {"start": 20000, "end": 59999},
            },
        }
        _dump_yaml(NETWORKS_FILE, networks_doc)

    if PORTS_FILE.is_file():
        PORTS_FILE.unlink()

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
