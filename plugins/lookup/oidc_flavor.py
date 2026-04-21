from __future__ import annotations

from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.applications.config import get


_APPLICATION_ID = "web-app-nextcloud"


class LookupModule(LookupBase):
    """
    lookup('oidc_flavor')

    Resolves the effective OIDC plugin flavor for the Nextcloud role.

    Resolution order:
      1. An explicit string value at applications['web-app-nextcloud']
         .compose.services.oidc.flavor (inventory override).
      2. "oidc_login" if compose.services.ldap.enabled is truthy
         (pulsejet/nextcloud-oidc-login, proxy-LDAP capable).
      3. "sociallogin" otherwise (nextcloud/sociallogin).

    Mirrors the former `_applications_nextcloud_oidc_flavor` group_vars helper
    that was removed in commit 77a0e16ea.
    """

    def run(self, terms, variables: Optional[Dict[str, Any]] = None, **kwargs):
        if terms:
            raise AnsibleError("lookup('oidc_flavor') takes no positional terms.")

        if variables is None or "applications" not in variables:
            raise AnsibleError(
                "lookup('oidc_flavor'): 'applications' variable not defined."
            )

        applications = variables["applications"]
        if not isinstance(applications, dict):
            raise AnsibleError(
                "lookup('oidc_flavor'): 'applications' must be a dict/mapping."
            )

        explicit = get(
            applications=applications,
            application_id=_APPLICATION_ID,
            config_path="compose.services.oidc.flavor",
            strict=False,
            default=None,
            skip_missing_app=True,
        )
        if isinstance(explicit, str) and explicit.strip():
            return [explicit.strip()]

        ldap_enabled = bool(
            get(
                applications=applications,
                application_id=_APPLICATION_ID,
                config_path="compose.services.ldap.enabled",
                strict=False,
                default=False,
                skip_missing_app=True,
            )
        )

        return ["oidc_login" if ldap_enabled else "sociallogin"]
