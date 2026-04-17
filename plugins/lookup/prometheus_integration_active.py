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
      {% if lookup('prometheus_integration_active') %}
      ...prometheus monitoring block...
      {% endif %}
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

        group_names: List[str] = vars_.get("group_names", [])
        application_id: str = vars_.get("application_id", "")

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
