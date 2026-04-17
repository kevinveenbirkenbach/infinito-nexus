from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf


class LookupModule(LookupBase):
    """
    Return a sorted list of deployed application IDs that satisfy both:
      1. native_metrics.enabled: true in their role config
      2. a prometheus.yml.j2 template at roles/<app_id>/templates/

    Used by web-app-prometheus/templates/configuration/prometheus.yml.j2 to auto-discover apps
    that expose a native /metrics endpoint without hardcoding each app name.

    Usage in a template:
      {% for app_id in lookup('native_metrics_apps') %}
      {% include 'roles/' + app_id + '/templates/prometheus.yml.j2' %}
      {% endfor %}
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[List[str]]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        applications = vars_.get("applications")
        if not isinstance(applications, dict):
            raise AnsibleError(
                "native_metrics_apps: required variable 'applications' must be a mapping"
            )

        group_names: List[str] = vars_.get("group_names", [])
        roles_dir = self._find_roles_dir()

        result: List[str] = []
        for app_id in sorted(applications.keys()):
            if app_id not in group_names:
                continue
            enabled = get_app_conf(
                applications=applications,
                application_id=app_id,
                config_path="native_metrics.enabled",
                strict=False,
                default=False,
                skip_missing_app=True,
            )
            if not enabled:
                continue

            scrape_template = roles_dir / app_id / "templates" / "prometheus.yml.j2"
            if scrape_template.exists():
                result.append(app_id)

        return [result]

    def _find_roles_dir(self) -> Path:
        candidates = [
            Path(os.getcwd()) / "roles",
            Path(__file__).resolve().parent.parent.parent / "roles",
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        raise AnsibleError("native_metrics_apps: cannot locate roles/ directory")
