# lookup_plugins/tls_resolve.py
#
# STRICT TLS resolver (without SAN/cert identity planning).
#
# Certificate identity planning (SAN list, cert/key paths) is moved to:
#   lookup_plugins/cert_plan.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.tls_common import (
    AVAILABLE_FLAVORS,
    as_str,
    collect_domains_for_app,
    require,
    resolve_enabled,
    resolve_mode,
    resolve_term,
    uniq_preserve,
    want_get,
)


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        if not terms or len(terms) != 1:
            raise AnsibleError(
                "tls_resolve: exactly one term required (domain or application_id)"
            )

        term = as_str(terms[0])
        if not term:
            raise AnsibleError("tls_resolve: term is empty")

        domains = require(variables, "domains", dict)
        applications = require(variables, "applications", dict)
        enabled_default = require(variables, "TLS_ENABLED", (bool, int))
        mode_default = as_str(require(variables, "TLS_MODE", str))

        if mode_default not in AVAILABLE_FLAVORS:
            raise AnsibleError(
                f"tls_resolve: TLS_MODE must be one of {sorted(AVAILABLE_FLAVORS)}, got '{mode_default}'"
            )

        forced_mode = as_str(kwargs.get("mode", "auto")).lower()

        app_id, primary_domain = resolve_term(
            term,
            domains=domains,
            applications=applications,
            forced_mode=forced_mode,
            err_prefix="tls_resolve",
        )

        all_domains = collect_domains_for_app(domains, app_id, err_prefix="tls_resolve")
        all_domains = (
            uniq_preserve([primary_domain] + all_domains)
            if all_domains
            else [primary_domain]
        )

        app = applications.get(app_id, {})
        if not isinstance(app, dict):
            app = {}

        enabled = resolve_enabled(app, bool(enabled_default))
        mode = resolve_mode(app, enabled, mode_default, err_prefix="tls_resolve")

        if mode not in {"off"} | AVAILABLE_FLAVORS:
            raise AnsibleError(
                f"tls_resolve: unsupported mode '{mode}' for app '{app_id}'"
            )

        web_protocol = "https" if enabled else "http"
        websocket_protocol = "wss" if enabled else "ws"
        web_port = 443 if enabled else 80
        base_url = f"{web_protocol}://{primary_domain}/"

        resolved: Dict[str, Any] = {
            "application_id": app_id,
            "domain": primary_domain,
            "enabled": enabled,
            "mode": mode,
            "domains": {"primary": primary_domain, "all": all_domains},
            "protocols": {"web": web_protocol, "websocket": websocket_protocol},
            "ports": {"web": web_port},
            "url": {"base": base_url},
        }

        want = as_str(kwargs.get("want", ""))
        if want:
            return [want_get(resolved, want)]
        return [resolved]
