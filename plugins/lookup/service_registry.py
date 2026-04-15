from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.service_registry import (
    build_service_registry_from_applications,
    ordered_primary_service_entries,
)


class LookupModule(LookupBase):
    """
    Discover the role-local service registry.

    Usage:
      {{ query('service_registry') | first }}
      {{ query('service_registry', 'ordered') | first }}
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Any]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}
        applications = kwargs.get("applications", vars_.get("applications"))
        if not isinstance(applications, dict):
            raise AnsibleError(
                "service_registry: required variable 'applications' must be a mapping"
            )

        roles_dir = Path(kwargs.get("roles_dir") or Path.cwd() / "roles")
        registry = build_service_registry_from_applications(applications)
        mode = str(terms[0]).strip() if terms else "mapping"

        if mode in {"mapping", ""}:
            return [registry]
        if mode == "ordered":
            return [ordered_primary_service_entries(registry, roles_dir)]

        raise AnsibleError(
            f"service_registry: unsupported mode '{mode}' (expected 'mapping' or 'ordered')"
        )
