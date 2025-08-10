# roles/web-app-keycloak/filter_plugins/redirect_uris.py
from __future__ import annotations
import os, sys
from typing import Iterable, Sequence
from ansible.errors import AnsibleFilterError

# --- Locate project root that contains `module_utils/` dynamically (up to 5 levels) ---
def _ensure_module_utils_on_path():
    here = os.path.dirname(__file__)
    for depth in range(1, 6):
        candidate = os.path.abspath(os.path.join(here, *(['..'] * depth)))
        if os.path.isdir(os.path.join(candidate, 'module_utils')):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return
    # If not found, imports below will raise a clear error
_ensure_module_utils_on_path()

# Import your existing helpers
from module_utils.config_utils import get_app_conf, AppConfigKeyError, ConfigEntryNotSetError
from module_utils.get_url import get_url  # returns "<protocol>://<domain>"

def _stable_dedup(items: Sequence[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def redirect_uris(domains: dict,
                  applications: dict,
                  web_protocol: str = "https",
                  wildcard: str = "/*",
                  features: Iterable[str] = ("features.oauth2", "features.oidc"),
                  dedup: bool = True) -> list[str]:
    """
    Build redirect URIs using:
      - get_app_conf(applications, app_id, dotted_key, default) for feature gating
      - get_url(domains_subset, app_id, web_protocol) to form "<proto>://<domain>"

    For domain lists, we call get_url() once per domain by passing a minimal
    per-app subset like {app_id: "example.org"} to preserve your original
    'one entry per domain' behavior.
    """
    if not isinstance(domains, dict):
        raise AnsibleFilterError("redirect_uris: 'domains' must be a dict mapping app_id -> domain or list of domains")

    uris: list[str] = []

    for app_id, domain_value in domains.items():
        # Feature check via get_app_conf
        try:
            has_feature = any(bool(get_app_conf(applications, app_id, f, False)) for f in features)
        except (AppConfigKeyError, ConfigEntryNotSetError):
            has_feature = False

        if not has_feature:
            continue

        # Normalize to iterable of domains
        doms = [domain_value] if isinstance(domain_value, str) else list(domain_value or [])

        for d in doms:
            # Use get_url() to produce "<proto>://<domain>"
            # Pass a minimal per-app mapping so get_domain() resolves to 'd'
            try:
                url = get_url({app_id: d}, app_id, web_protocol)
            except Exception as e:
                raise AnsibleFilterError(f"redirect_uris: get_url failed for app '{app_id}' with domain '{d}': {e}")
            uris.append(f"{url}{wildcard}")

    return _stable_dedup(uris) if dedup else uris


class FilterModule(object):
    """Infinito.Nexus redirect URI builder (uses get_app_conf + get_url)"""
    def filters(self):
        return {
            "redirect_uris": redirect_uris,
        }
