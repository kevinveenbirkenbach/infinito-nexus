from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):
    """
    Return True when the prometheus monitoring block should be emitted for the
    current application on the current host; False otherwise.

    The condition satisfied:
      1. 'web-app-prometheus' is in group_names (prometheus is deployed on this host), AND
      2. Either the current application IS web-app-prometheus, OR it declares prometheus
         as an enabled compose service dependency (compose.services.prometheus.enabled: true).

    Usage in a template:
      {% if lookup('prometheus_integration_active', application_id) %}
      ...prometheus monitoring block...
      {% endif %}

    Pass 'application_id' as term 0 (string). 'applications' is read from
    available_variables — the same source used by lookup('config') and lookup('database').
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[bool]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        applications = vars_.get("applications")
        if not isinstance(applications, dict):
            raise AnsibleError(
                "prometheus_integration_active: required variable 'applications' must be a mapping"
            )

        # application_id may be passed explicitly (term 0) or read from available_variables.
        if terms and isinstance(terms[0], str):
            application_id: str = terms[0]
        else:
            application_id = vars_.get("application_id", "")

        group_names: List[str] = vars_.get("group_names", [])

        if "web-app-prometheus" not in group_names:
            return [False]

        if application_id == "web-app-prometheus":
            return [True]

        try:
            enabled = bool(
                applications.get(application_id, {})
                .get("compose", {})
                .get("services", {})
                .get("prometheus", {})
                .get("enabled", False)
            )
        except Exception:
            enabled = False

        return [enabled]
