# lookup_plugins/tls_resolve.py
#
# strict tls resolver for infinito.nexus.
#
# usage:
#   {{ lookup('tls_resolve', 'meet.infinito.example') }}                # domain
#   {{ lookup('tls_resolve', 'web-app-bigbluebutton') }}                # application_id
#   {{ lookup('tls_resolve', 'meet.infinito.example', want='files.cert') }}
#   {{ lookup('tls_resolve', 'web-app-bigbluebutton', want='protocols.web') }}
#   {{ lookup('tls_resolve', 'meet.infinito.example', want='url.base') }}
#   {{ lookup('tls_resolve', 'meet.infinito.example', mode='domain') }} # force domain
#   {{ lookup('tls_resolve', 'web-app-bigbluebutton', mode='app') }}    # force app
#
# required context vars (no fallbacks):
#   - domains (dict)
#   - applications (dict)
#   - TLS_ENABLED (bool/int)
#   - TLS_MODE (str: "letsencrypt" | "self_signed")
#   - LETSENCRYPT_BASE_PATH (str)
#   - LETSENCRYPT_LIVE_PATH (str)
#
# optional per-app overrides:
#   - applications[app].server.tls.enabled
#   - applications[app].server.tls.flavor
#   - applications[app].server.tls.letsencrypt_cert_name
#   - applications[app].server.tls.domains_san
#
# conditional required:
#   - tls_selfsigned_base (str) only if mode == "self_signed"
#
# output keys:
#   - enabled, mode
#   - domains.primary, domains.all, domains.san
#   - files.cert, files.key, files.ca
#   - protocols.web, protocols.websocket
#   - ports.web
#   - url.base
#   - application_id, domain
#
# Notes:
# - "domains.all" is derived from the global "domains" mapping for the resolved application_id.
# - "domains.san" is either the explicit per-app override (plus primary), or defaults to "domains.all".

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


AVAILABLE_FLAVORS = {"letsencrypt", "self_signed"}
LE_FULLCHAIN = "fullchain.pem"
LE_PRIVKEY = "privkey.pem"


# -------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------


def _as_str(value: Any) -> str:
    return str(value).strip()


def _norm_domain(value: Any) -> str:
    return _as_str(value).lower()


def _join(*parts: Any) -> str:
    cleaned = [str(p).strip() for p in parts if str(p).strip()]
    return os.path.join(*cleaned) if cleaned else ""


def _require(variables: dict, name: str, expected_type: type | tuple[type, ...]) -> Any:
    if name not in variables:
        raise AnsibleError(f"tls_resolve: required variable '{name}' is missing")
    value = variables[name]
    if not isinstance(value, expected_type):
        raise AnsibleError(
            f"tls_resolve: variable '{name}' must be {expected_type}, got {type(value).__name__}"
        )
    return value


def _get_path(data: Any, path: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _want_get(data: Any, dotted: str) -> Any:
    if not dotted:
        return data
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise AnsibleError(
                f"tls_resolve: want='{dotted}' not found (missing '{part}')"
            )
        cur = cur[part]
    return cur


def _iter_domains(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return

    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, str) and v.strip():
                yield v.strip()
        return

    if isinstance(value, list):
        for v in value:
            if isinstance(v, str) and v.strip():
                yield v.strip()
        return


def _uniq_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        s = _as_str(it)
        if not s:
            continue
        s = _norm_domain(s)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


# -------------------------------------------------------------------
# resolution helpers
# -------------------------------------------------------------------


def _resolve_app_id_from_domain(domains: dict, domain: str) -> str:
    needle = _norm_domain(domain)
    matches: list[str] = []

    for app_id, val in domains.items():
        for d in _iter_domains(val):
            if _norm_domain(d) == needle:
                matches.append(str(app_id))

    if not matches:
        raise AnsibleError(
            f"tls_resolve: domain '{domain}' not found in domains mapping"
        )

    if len(matches) > 1:
        raise AnsibleError(
            f"tls_resolve: domain '{domain}' is ambiguous, matches applications {matches}"
        )

    return matches[0]


def _resolve_primary_domain_from_app(domains: dict, app_id: str) -> str:
    if app_id not in domains:
        raise AnsibleError(
            f"tls_resolve: application_id '{app_id}' not found in domains mapping"
        )

    val = domains[app_id]

    if isinstance(val, str):
        if not val:
            raise AnsibleError(f"tls_resolve: domains['{app_id}'] is empty")
        return val

    if isinstance(val, dict):
        try:
            first_val = next(iter(val.values()))
        except StopIteration:
            raise AnsibleError(f"tls_resolve: domains['{app_id}'] dict is empty")
        if not isinstance(first_val, str) or not first_val:
            raise AnsibleError(f"tls_resolve: invalid primary domain for '{app_id}'")
        return first_val

    if isinstance(val, list):
        if not val:
            raise AnsibleError(f"tls_resolve: domains['{app_id}'] list is empty")
        first = val[0]
        if not isinstance(first, str) or not first:
            raise AnsibleError(f"tls_resolve: invalid primary domain for '{app_id}'")
        return first

    raise AnsibleError(
        f"tls_resolve: domains['{app_id}'] has unsupported type {type(val).__name__}"
    )


def _collect_domains_for_app(domains: dict, app_id: str) -> list[str]:
    """
    Return all domains configured for an app from the global domains mapping.
    Supports:
      - str: single domain
      - dict: values are domains (e.g. canonical/api/view/etc)
      - list: list of domains
    """
    if app_id not in domains:
        raise AnsibleError(
            f"tls_resolve: application_id '{app_id}' not found in domains mapping"
        )
    return _uniq_preserve(list(_iter_domains(domains[app_id])))


def _override_san_list(app: dict) -> list[str] | None:
    """
    Optional per-app SAN override: applications[app].server.tls.domains_san
    Accepts string or list of strings. Returns None if not set.
    """
    raw = _get_path(app, "server.tls.domains_san", None)
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return []


def _resolve_enabled(app: dict, enabled_default: bool) -> bool:
    override = _get_path(app, "server.tls.enabled", None)
    return enabled_default if override is None else bool(override)


def _resolve_mode(app: dict, enabled: bool, mode_default: str) -> str:
    if not enabled:
        return "off"
    override = _get_path(app, "server.tls.flavor", None)
    if isinstance(override, str) and override.strip():
        return override.strip()
    return mode_default


def _resolve_le_name(app: dict, domain: str) -> str:
    override = _get_path(app, "server.tls.letsencrypt_cert_name", "")
    name = _as_str(override)
    return name or domain


# -------------------------------------------------------------------
# lookup
# -------------------------------------------------------------------


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        if not terms or len(terms) != 1:
            raise AnsibleError(
                "tls_resolve: exactly one term required (domain or application_id)"
            )

        term = _as_str(terms[0])
        if not term:
            raise AnsibleError("tls_resolve: term is empty")

        # required context vars
        domains = _require(variables, "domains", dict)
        applications = _require(variables, "applications", dict)
        enabled_default = _require(variables, "TLS_ENABLED", (bool, int))
        mode_default = _as_str(_require(variables, "TLS_MODE", str))
        _require(variables, "LETSENCRYPT_BASE_PATH", str)
        le_live = _as_str(_require(variables, "LETSENCRYPT_LIVE_PATH", str))

        if mode_default not in AVAILABLE_FLAVORS:
            raise AnsibleError(
                f"tls_resolve: TLS_MODE must be one of {sorted(AVAILABLE_FLAVORS)}, "
                f"got '{mode_default}'"
            )

        forced = _as_str(kwargs.get("mode", "auto")).lower()
        if forced not in {"auto", "domain", "app"}:
            raise AnsibleError("tls_resolve: mode must be one of: auto, domain, app")

        # determine input type
        if forced == "domain":
            is_domain = True
        elif forced == "app":
            is_domain = False
        else:
            is_domain = "." in term

        if is_domain:
            domain = term
            app_id = _resolve_app_id_from_domain(domains, domain)
        else:
            app_id = term
            domain = _resolve_primary_domain_from_app(domains, app_id)

        # normalize and collect domain sets
        primary_domain = _norm_domain(domain)
        all_domains = _collect_domains_for_app(domains, app_id)
        all_domains = (
            _uniq_preserve([primary_domain] + all_domains)
            if all_domains
            else [primary_domain]
        )

        app = applications.get(app_id, {})
        if not isinstance(app, dict):
            app = {}

        enabled = _resolve_enabled(app, bool(enabled_default))
        mode = _resolve_mode(app, enabled, mode_default)

        if mode not in {"off"} | AVAILABLE_FLAVORS:
            raise AnsibleError(
                f"tls_resolve: unsupported mode '{mode}' for app '{app_id}'"
            )

        cert_file = ""
        key_file = ""
        ca_file = ""

        if mode == "letsencrypt":
            le_name = _resolve_le_name(app, primary_domain)
            cert_file = _join(le_live, le_name, LE_FULLCHAIN)
            key_file = _join(le_live, le_name, LE_PRIVKEY)

        elif mode == "self_signed":
            ss_base = _as_str(_require(variables, "tls_selfsigned_base", str))
            cert_file = _join(ss_base, app_id, primary_domain, LE_FULLCHAIN)
            key_file = _join(ss_base, app_id, primary_domain, LE_PRIVKEY)

        web_protocol = "https" if enabled else "http"
        websocket_protocol = "wss" if enabled else "ws"
        web_port = 443 if enabled else 80

        base_url = f"{web_protocol}://{primary_domain}/"

        san_override = _override_san_list(app)
        if san_override is None:
            san_domains = all_domains[:] if all_domains else [primary_domain]
        else:
            san_domains = _uniq_preserve([primary_domain] + san_override)

        resolved: Dict[str, Any] = {
            "application_id": app_id,
            "domain": primary_domain,
            "enabled": enabled,
            "mode": mode,
            "domains": {
                "primary": primary_domain,
                "all": all_domains,
                "san": san_domains,
            },
            "files": {
                "cert": cert_file,
                "key": key_file,
                "ca": ca_file,
            },
            "protocols": {
                "web": web_protocol,
                "websocket": websocket_protocol,
            },
            "ports": {
                "web": web_port,
            },
            "url": {
                "base": base_url,
            },
        }

        want = _as_str(kwargs.get("want", ""))
        if want:
            return [_want_get(resolved, want)]

        return [resolved]
