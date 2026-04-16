from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf

# Role that owns the alerting configuration (webhook URLs, credentials).
PROMETHEUS_APP_ID: str = "web-app-prometheus"

# Maps each communication-channel app to the config path (relative to
# PROMETHEUS_APP_ID) whose value must be non-empty for the alertmanager
# receiver to be considered active.
# - None  → always active (email via mailu is unconditional)
# - str   → config path; receiver is active iff the resolved value is truthy
# Add new entries here when a new alertmanager receiver is implemented.
# Remove an app from this dict to exclude it until its receiver is ready.
RECEIVER_CONFIG: Dict[str, Optional[str]] = {
    "web-app-mailu": None,  # email — always active
    "web-app-mattermost": "alerting.mattermost.webhook_url",
}


class LookupModule(LookupBase):
    """
    Return the subset of communication-channel apps that are both deployed on this
    host AND have a configured alertmanager receiver.

    Deployment check : app ID must appear in group_names (the current host's groups).
    Receiver check   : config path in RECEIVER_CONFIG must resolve to a non-empty value.
                       Both checks read from config (SPOT) — no dependency on derived vars.

    Candidate list   : derived from RECEIVER_CONFIG keys.
                       To add a new channel, add it to RECEIVER_CONFIG.
                       To defer a channel, simply omit it until its receiver is ready.

    Usage in a template:
      {{ lookup('active_alertmanager_channels') | join('|') }}
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
                "active_alertmanager_channels: required variable 'applications' must be a mapping"
            )

        group_names: List[str] = vars_.get("group_names", [])

        # Candidate list is derived from RECEIVER_CONFIG — the plugin is the SPOT.
        candidates: List[str] = list(RECEIVER_CONFIG)

        result: List[str] = []
        for app_id in candidates:
            # 1. Must be deployed on this host.
            if app_id not in group_names:
                continue

            config_path = RECEIVER_CONFIG[app_id]
            if config_path is None:
                # Unconditionally active (e.g. web-app-mailu — email always works).
                result.append(app_id)
            else:
                # Active only when the config value is set and non-empty.
                value = get_app_conf(
                    applications=applications,
                    application_id=PROMETHEUS_APP_ID,
                    config_path=config_path,
                    strict=False,
                    default="",
                    skip_missing_app=True,
                )
                if value and str(value).strip():
                    result.append(app_id)

        return [result]
