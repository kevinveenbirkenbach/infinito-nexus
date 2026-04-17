from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf


class LookupModule(LookupBase):
    """
    Return a sorted list of communication-channel app IDs that are deployed on
    this host.

    Deployment check  : app ID must appear in group_names.
    Channel check     : app must declare communication.channel: true in its own
                        role config — the self-declaration pattern (SPOT per app,
                        no hardcoded list anywhere).

    Usage in a template:
      {% set _comm_channels = lookup('active_alertmanager_channels', applications) %}

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
    ) -> List[List[str]]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        # Prefer explicitly passed applications (template context) over available_variables
        # (which may be the pre-merge inventory dict in some Ansible scoping scenarios).
        if terms and isinstance(terms[0], dict):
            applications = terms[0]
        else:
            applications = vars_.get("applications")

        if not isinstance(applications, dict):
            raise AnsibleError(
                "active_alertmanager_channels: required variable 'applications' must be a mapping"
            )

        group_names: List[str] = vars_.get("group_names", [])

        result: List[str] = []
        for app_id in sorted(applications.keys()):
            if app_id not in group_names:
                continue

            is_channel = get_app_conf(
                applications=applications,
                application_id=app_id,
                config_path="communication.channel",
                strict=False,
                default=False,
                skip_missing_app=True,
            )
            if is_channel:
                result.append(app_id)

        return [result]
