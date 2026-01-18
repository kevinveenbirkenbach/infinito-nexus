from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Set, Tuple

import yaml

from .errors import ServicesResolutionError


def _stable_dedup(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _as_mapping(obj: object) -> dict:
    return obj if isinstance(obj, dict) else {}


def _is_enabled_shared(svc: object) -> bool:
    svc = _as_mapping(svc)
    return svc.get("enabled") is True and svc.get("shared") is True


def _is_enabled(svc: object) -> bool:
    svc = _as_mapping(svc)
    return svc.get("enabled") is True


@dataclass(frozen=True)
class ServiceRule:
    """
    One rule:
      - if predicate(service_cfg) is True -> include mapper(service_cfg)
    """

    service_name: str
    predicate: Callable[[object], bool]
    mapper: Callable[[dict], str]


def resolve_direct_service_roles_from_config(config: dict) -> List[str]:
    """
    Single source of truth for "service -> provider role(s)" mapping.

    Semantics (intentionally specific to Infinito.Nexus):
      - ldap enabled+shared    => svc-db-openldap
      - oidc enabled+shared    => web-app-keycloak
      - matomo enabled+shared  => web-app-matomo
      - coturn enabled+shared  => web-svc-coturn
      - onlyoffice enabled+shared => web-svc-onlyoffice
      - database enabled+shared => svc-db-<type> (requires database.type)
      - desktop enabled        => web-app-desktop   (shared does NOT matter)
    """
    cfg = _as_mapping(config)
    services = _as_mapping(_as_mapping(cfg.get("docker")).get("services"))

    def map_database(svc: dict) -> str:
        db_type = (svc.get("type") or "").strip()
        if not db_type:
            raise ServicesResolutionError(
                "docker.services.database.enabled=true and shared=true but docker.services.database.type is missing"
            )
        return f"svc-db-{db_type}"

    rules: Tuple[ServiceRule, ...] = (
        ServiceRule("ldap", _is_enabled_shared, lambda _svc: "svc-db-openldap"),
        ServiceRule("oidc", _is_enabled_shared, lambda _svc: "web-app-keycloak"),
        ServiceRule("matomo", _is_enabled_shared, lambda _svc: "web-app-matomo"),
        ServiceRule("coturn", _is_enabled_shared, lambda _svc: "web-svc-coturn"),
        ServiceRule(
            "onlyoffice", _is_enabled_shared, lambda _svc: "web-svc-onlyoffice"
        ),
        ServiceRule("database", _is_enabled_shared, map_database),
        ServiceRule("desktop", _is_enabled, lambda _svc: "web-app-desktop"),
    )

    includes: List[str] = []
    for rule in rules:
        svc_obj = services.get(rule.service_name)
        if rule.predicate(svc_obj):
            includes.append(rule.mapper(_as_mapping(svc_obj)))

    return _stable_dedup(includes)


class ServicesResolver:
    """
    Resolve shared-provider roles transitively from role config/main.yml.

    Note:
    - Transitively follows provider roles by reading THEIR configs and applying the same
      resolve_direct_service_roles_from_config() logic.
    """

    def __init__(self, roles_root: Path) -> None:
        self.roles_root = roles_root

    def _role_dir(self, role_name: str) -> Path:
        return self.roles_root / role_name

    def _role_config_path(self, role_name: str) -> Path:
        return self._role_dir(role_name) / "config" / "main.yml"

    def _load_role_config(self, role_name: str) -> dict:
        cfg_path = self._role_config_path(role_name)
        if not cfg_path.exists():
            return {}
        try:
            return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise ServicesResolutionError(f"Failed to parse {cfg_path}: {exc}") from exc

    def _validate_role_exists(self, role_name: str) -> None:
        role_dir = self._role_dir(role_name)
        if not role_dir.is_dir():
            raise ServicesResolutionError(
                f"Resolved service role {role_name!r} does not exist (missing folder {role_dir})"
            )

    def direct_includes_from_config(self, config: dict) -> List[str]:
        return resolve_direct_service_roles_from_config(config)

    def resolve_transitively(self, root_role_name: str) -> List[str]:
        """
        BFS over roles discovered via service flags.
        Queue order is stable, results are deduped.
        """
        resolved: List[str] = []
        seen: Set[str] = set()

        root_cfg = self._load_role_config(root_role_name)
        queue: List[str] = self.direct_includes_from_config(root_cfg)

        while queue:
            role_name = queue.pop(0)
            if role_name in seen:
                continue

            self._validate_role_exists(role_name)

            seen.add(role_name)
            resolved.append(role_name)

            cfg = self._load_role_config(role_name)
            for inc in self.direct_includes_from_config(cfg):
                if inc not in seen:
                    queue.append(inc)

        return resolved
