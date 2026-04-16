from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.config_utils import get_app_conf

# Maps each communication-channel app to the config path (relative to
# web-app-prometheus) whose value must be non-empty for the alertmanager
# receiver to be considered active.
# - None  → always active (email via mailu is unconditional)
# - str   → config path; receiver is active iff the resolved value is truthy
# Add new entries here when a new alertmanager receiver is implemented.
_RECEIVER_CONFIG: Dict[str, Optional[str]] = {
    "web-app-mailu": None,  # email — always active
    "web-app-mattermost": "alerting.mattermost.webhook_url",
    "web-app-matrix": None,  # placeholder — no native receiver yet; excluded via _NO_RECEIVER
}

# Channels with no alertmanager receiver implemented yet — excluded unconditionally
# until a receiver is added. Remove from here and update _RECEIVER_CONFIG when ready.
_NO_RECEIVER: frozenset = frozenset({"web-app-matrix"})


class LookupModule(LookupBase):
    """
    Return the subset of alerting.communication_channels (from web-app-prometheus
    config) that are both deployed on this host AND have a configured alertmanager
    receiver.

    Deployment check : app ID must appear in group_names (the current host's groups).
    Receiver check   : config path in _RECEIVER_CONFIG must resolve to a non-empty value.
                       Both checks read from config (SPOT) — no dependency on derived vars.

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

        candidates: List[str] = (
            get_app_conf(
                applications=applications,
                application_id="web-app-prometheus",
                config_path="alerting.communication_channels",
                strict=False,
                default=[],
                skip_missing_app=True,
            )
            or []
        )

        result: List[str] = []
        for app_id in candidates:
            # 1. Must be deployed on this host.
            if app_id not in group_names:
                continue

            # 2. No receiver implemented yet — skip entirely.
            if app_id in _NO_RECEIVER:
                continue

            config_path = _RECEIVER_CONFIG.get(app_id)
            if config_path is None:
                # Unconditionally active (e.g. web-app-mailu — email always works).
                result.append(app_id)
            else:
                # Active only when the config value is set and non-empty.
                value = get_app_conf(
                    applications=applications,
                    application_id="web-app-prometheus",
                    config_path=config_path,
                    strict=False,
                    default="",
                    skip_missing_app=True,
                )
                if value and str(value).strip():
                    result.append(app_id)

        return [result]
