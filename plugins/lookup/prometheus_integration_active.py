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
      {% if lookup('prometheus_integration_active', applications) %}
      ...prometheus monitoring block...
      {% endif %}

    The caller MUST pass the 'applications' dict as the first positional term.
    Lookup plugins receive available_variables from the templar, which may hold
    the pre-merge inventory dict instead of the set_fact-merged result. Passing
    'applications' explicitly from the template context ensures the correct merged
    dict is always used.
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[bool]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        # Prefer explicitly passed applications (template context) over available_variables
        # (which may be the pre-merge inventory dict in some Ansible scoping scenarios).
        if terms and isinstance(terms[0], dict):
            applications = terms[0]
        else:
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
