from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf


def _require_non_empty(value: Any, name: str) -> str:
    s = str(value).strip()
    if not s:
        raise AnsibleError(f"service_should_load: '{name}' must not be empty")
    return s


def _service_enabled_and_shared(
    applications: Dict[str, Any],
    application_id: str,
    service_name: str,
    default: bool,
) -> bool:
    enabled = get_app_conf(
        applications=applications,
        application_id=application_id,
        config_path=f"compose.services.{service_name}.enabled",
        strict=False,
        default=default,
        skip_missing_app=False,
    )
    shared = get_app_conf(
        applications=applications,
        application_id=application_id,
        config_path=f"compose.services.{service_name}.shared",
        strict=False,
        default=default,
        skip_missing_app=False,
    )
    return bool(enabled) and bool(shared)


def _run_once_var_name(service_id: str) -> str:
    return f"run_once_{service_id.replace('-', '_')}"


class LookupModule(LookupBase):
    """
    Evaluate whether a backend service should be loaded.

    Usage:
      {{ query('service_should_load', service_id, application_id=application_id, service_name=service_name) | first }}
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[bool]:
        if not terms:
            return []

        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}
        applications = kwargs.get("applications", vars_.get("applications"))
        if not isinstance(applications, dict):
            raise AnsibleError(
                "service_should_load: required variable 'applications' must be a mapping"
            )

        application_id = _require_non_empty(
            kwargs.get("application_id", vars_.get("application_id")), "application_id"
        )
        service_name = _require_non_empty(
            kwargs.get("service_name", vars_.get("service_name")), "service_name"
        )
        default = bool(kwargs.get("default", False))

        results: List[bool] = []
        for term in terms:
            service_id = _require_non_empty(term, "service_id")
            run_once_defined = _run_once_var_name(service_id) in vars_
            should_load = (
                _service_enabled_and_shared(
                    applications=applications,
                    application_id=application_id,
                    service_name=service_name,
                    default=default,
                )
                and (not run_once_defined)
                and (application_id != service_id)
            )
            results.append(bool(should_load))

        return results
