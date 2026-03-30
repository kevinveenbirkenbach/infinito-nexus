from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf


def _get_service_flag(
    applications: Dict[str, Any],
    app_id: str,
    service_key: str,
    flag: str,
) -> bool:
    return bool(
        get_app_conf(
            applications=applications,
            application_id=app_id,
            config_path=f"compose.services.{service_key}.{flag}",
            strict=False,
            default=False,
            skip_missing_app=True,
        )
    )


def _get_enabled_service_keys(
    applications: Dict[str, Any],
    app_id: str,
) -> List[str]:
    services = get_app_conf(
        applications=applications,
        application_id=app_id,
        config_path="compose.services",
        strict=False,
        default={},
        skip_missing_app=True,
    )
    if not isinstance(services, dict):
        return []
    return [
        k
        for k, v in services.items()
        if isinstance(v, dict) and v.get("enabled", False)
    ]


def _is_service_needed(
    applications: Dict[str, Any],
    app_id: str,
    service_key: str,
    visited: Set[str],
) -> bool:
    """
    Return True if app_id directly or transitively (via its enabled services)
    has service_key with both enabled: true AND shared: true.
    Uses visited to prevent infinite loops.
    """
    if app_id in visited:
        return False
    visited.add(app_id)

    enabled = _get_service_flag(applications, app_id, service_key, "enabled")
    shared = _get_service_flag(applications, app_id, service_key, "shared")
    if enabled and shared:
        return True

    for svc in _get_enabled_service_keys(applications, app_id):
        if svc == service_key:
            continue
        if svc in applications:
            if _is_service_needed(applications, svc, service_key, visited):
                return True

    return False


def _build_role_to_key(services_map: Dict[str, Any]) -> Dict[str, str]:
    """Map each role name to its canonical service key.

    When multiple keys share the same role, the canonical key is determined by
    the 'canonical' field on alias entries.  The primary key (no 'canonical'
    field) is used as the fallback so that role-based reverse lookup always
    returns a single, deterministic id.
    """
    result: Dict[str, str] = {}
    for key, entry in services_map.items():
        if not isinstance(entry, dict) or "role" not in entry:
            continue
        role = entry["role"]
        canonical_key = entry.get("canonical", key)
        result[role] = canonical_key
    return result


def _resolve_term(
    term: str,
    services_map: Dict[str, Any],
    role_to_key: Dict[str, str],
) -> Tuple[str, str]:
    """
    Resolve a term (service key or role name) to (service_key, role).
    Raises AnsibleError if the term is not a known key or role.
    """
    if term in services_map:
        entry = services_map[term]
        role = entry.get("role") or entry.get("role_template", "")
        return term, str(role)
    if term in role_to_key:
        key = role_to_key[term]
        entry = services_map[key]
        role = entry.get("role") or entry.get("role_template", "")
        return key, str(role)
    raise AnsibleError(
        f"service: '{term}' is neither a known service key nor a known role name. "
        f"Known keys: {sorted(services_map)}. "
        f"Known roles: {sorted(role_to_key)}."
    )


def _compute_flags(
    applications: Dict[str, Any],
    group_names: List[str],
    service_key: str,
) -> Dict[str, bool]:
    deployed = [app_id for app_id in group_names if app_id in applications]
    any_enabled = any(
        _get_service_flag(applications, app_id, service_key, "enabled")
        for app_id in deployed
    )
    any_shared = any(
        _get_service_flag(applications, app_id, service_key, "shared")
        for app_id in deployed
    )
    any_needed = any(
        _is_service_needed(applications, app_id, service_key, set())
        for app_id in deployed
    )
    return {"enabled": any_enabled, "shared": any_shared, "needed": any_needed}


class LookupModule(LookupBase):
    """
    Resolve a service by key or role name and return its aggregated deployment flags.

    Usage:
      lookup('service', 'matomo')
      lookup('service', 'web-app-matomo')   # resolved via reverse mapping

    Reads 'applications', 'group_names', and 'services' from Ansible variables.
    The 'services' variable is the canonical key → role mapping from
    group_vars/all/20_services.yml and is automatically available in all plays.

    Returns a dict per term:
      id      — canonical service key  (e.g. 'matomo')
      role    — provider role name     (e.g. 'web-app-matomo')
      enabled — True if any deployed app has compose.services.<key>.enabled: true
      shared  — True if any deployed app has compose.services.<key>.shared: true
      needed  — True if any deployed app has both enabled AND shared (direct or
                transitively via its own enabled service dependencies)
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if not terms:
            return []

        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        applications = kwargs.get("applications", vars_.get("applications"))
        if not isinstance(applications, dict):
            raise AnsibleError(
                "service: required variable 'applications' must be a mapping"
            )

        group_names = kwargs.get("group_names", vars_.get("group_names", []))
        if not isinstance(group_names, list):
            raise AnsibleError(
                "service: required variable 'group_names' must be a list"
            )

        services_map = kwargs.get("services", vars_.get("services"))
        if not isinstance(services_map, dict):
            raise AnsibleError(
                "service: required variable 'services' must be a mapping "
                "(loaded from group_vars/all/20_services.yml)"
            )

        role_to_key = _build_role_to_key(services_map)

        results: List[Dict[str, Any]] = []
        for term in terms:
            term_str = str(term).strip()
            if not term_str:
                raise AnsibleError("service: service key/role must not be empty")

            service_key, role = _resolve_term(term_str, services_map, role_to_key)
            flags = _compute_flags(applications, group_names, service_key)
            results.append({"id": service_key, "role": role, **flags})

        return results
