from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import yaml

from .errors import ServicesResolutionError
from utils.service_registry import (
    build_service_registry_from_roles_dir,
    resolve_service_dependency_roles_from_config,
)

_ROLES_ROOT = Path(__file__).parents[5] / "roles"


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


def _load_service_registry(roles_root: Path = _ROLES_ROOT) -> Dict[str, Any]:
    try:
        return build_service_registry_from_roles_dir(roles_root)
    except Exception as exc:
        raise ServicesResolutionError(
            f"Failed to discover services from role configs in {roles_root}: {exc}"
        ) from exc


def resolve_direct_service_roles_from_config(
    config: dict,
    service_registry: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Single source of truth for "service -> provider role(s)" mapping.
    """
    if service_registry is None:
        service_registry = _load_service_registry()
    try:
        return _stable_dedup(
            resolve_service_dependency_roles_from_config(
                _as_mapping(config),
                service_registry,
            )
        )
    except Exception as exc:
        raise ServicesResolutionError(str(exc)) from exc


class ServicesResolver:
    """
    Resolve shared-provider roles transitively from role config/main.yml.

    Note:
    - Transitively follows provider roles by reading THEIR configs and applying the same
      resolve_direct_service_roles_from_config() logic.
    """

    def __init__(
        self,
        roles_root: Path,
        services_file: Path | None = None,
    ) -> None:
        self.roles_root = roles_root
        self._service_registry = _load_service_registry(
            services_file or self.roles_root
        )

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
                f"Resolved service role {role_name!r} does not exist "
                f"(missing folder {role_dir})"
            )

    def direct_includes_from_config(self, config: dict) -> List[str]:
        return resolve_direct_service_roles_from_config(config, self._service_registry)

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
