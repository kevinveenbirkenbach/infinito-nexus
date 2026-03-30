from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import yaml

from .errors import ServicesResolutionError

_SERVICES_FILE = Path(__file__).parents[5] / "group_vars" / "all" / "20_services.yml"


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


def _load_services_map(services_file: Path = _SERVICES_FILE) -> Dict[str, Any]:
    if not services_file.exists():
        raise ServicesResolutionError(f"20_services.yml not found at {services_file}")
    raw = yaml.safe_load(services_file.read_text(encoding="utf-8")) or {}
    services = raw.get("services")
    if not isinstance(services, dict):
        raise ServicesResolutionError(
            f"Expected a 'services' mapping in {services_file}"
        )
    return services


def resolve_direct_service_roles_from_config(
    config: dict,
    services_map: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Single source of truth for "service -> provider role(s)" mapping.

    Reads the service key → role mapping from services.yml (repo root).
    Every service requires compose.services.<key>.enabled: true AND shared: true.
    Entries with role_template substitute {type} from the service config.
    """
    if services_map is None:
        services_map = _load_services_map()

    cfg = _as_mapping(config)
    services = _as_mapping(_as_mapping(cfg.get("compose")).get("services"))

    includes: List[str] = []
    for key, mapping in services_map.items():
        svc_obj = services.get(key)
        if not _is_enabled_shared(svc_obj):
            continue

        role_template = mapping.get("role_template")
        if role_template:
            svc_dict = _as_mapping(svc_obj)
            db_type = (svc_dict.get("type") or "").strip()
            if not db_type:
                raise ServicesResolutionError(
                    f"compose.services.{key}.enabled=true and shared=true "
                    f"but compose.services.{key}.type is missing"
                )
            includes.append(role_template.format(type=db_type))
        else:
            includes.append(mapping["role"])

    return _stable_dedup(includes)


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
        services_file: Path = _SERVICES_FILE,
    ) -> None:
        self.roles_root = roles_root
        self._services_map = _load_services_map(services_file)

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
        return resolve_direct_service_roles_from_config(config, self._services_map)

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
