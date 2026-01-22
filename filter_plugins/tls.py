# filter_plugins/tls.py
#
# KISS TLS resolution helpers for Infinito.Nexus:
# - TLS_ENABLED is only a host default (must be passed explicitly)
# - applications[app_id].server.tls.* overrides per app
#
# Exposed filters:
# - tls_enabled(applications, app_id, tls_enabled_default) -> bool
# - tls_mode(applications, app_id, tls_enabled_default) -> str
# - tls_san(applications, app_id) -> list[str]
# - tls_le_name(applications, app_id) -> str
# - tls_web_protocol(applications, app_id, tls_enabled_default) -> str
# - tls_web_port(applications, app_id, tls_enabled_default) -> int
# - tls_websocket_protocol(applications, app_id, tls_enabled_default) -> str

from __future__ import annotations

from typing import Any


_AVAILABLE_FLAVORS = {"letsencrypt", "self_signed"}


def _get_path(d: Any, path: str, default: Any) -> Any:
    """Read dotted path from nested dict."""
    if not isinstance(d, dict):
        return default
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _get_app(applications: Any, application_id: str) -> dict:
    if not isinstance(applications, dict):
        return {}
    app = applications.get(application_id, {})
    return app if isinstance(app, dict) else {}


# -------------------------------------------------------------------
# Public Filters
# -------------------------------------------------------------------


def tls_enabled(
    applications: Any, application_id: str, tls_enabled_default: Any
) -> bool:
    """
    Effective TLS enabled flag:
    - applications[app].server.tls.enabled overrides
    - else fallback to tls_enabled_default (must be passed explicitly)
    """
    app = _get_app(applications, application_id)
    override = _get_path(app, "server.tls.enabled", None)

    if override is None:
        return bool(tls_enabled_default)

    return bool(override)


def tls_mode(applications: Any, application_id: str, tls_enabled_default: Any) -> str:
    """
    Effective TLS mode:
    - if tls is disabled -> "off"
    - else -> server.tls.flavor (fallback: 'letsencrypt')
    """
    if not tls_enabled(applications, application_id, tls_enabled_default):
        return "off"

    app = _get_app(applications, application_id)
    flavor = _get_path(app, "server.tls.flavor", "letsencrypt")

    if not isinstance(flavor, str):
        return "letsencrypt"

    flavor = flavor.strip()
    if not flavor:
        return "letsencrypt"

    return flavor if flavor in _AVAILABLE_FLAVORS else "letsencrypt"


def tls_san(applications: Any, application_id: str) -> list[str]:
    """Return SAN list from server.tls.domains_san (fallback: empty list)."""
    app = _get_app(applications, application_id)
    san = _get_path(app, "server.tls.domains_san", [])

    if san is None:
        return []

    if isinstance(san, list):
        return [str(x).strip() for x in san if str(x).strip()]

    if isinstance(san, str) and san.strip():
        return [san.strip()]

    return []


def tls_le_name(applications: Any, application_id: str) -> str:
    """Return Let's Encrypt cert name override (fallback: empty string)."""
    app = _get_app(applications, application_id)
    name = _get_path(app, "server.tls.letsencrypt_cert_name", "")
    return str(name).strip()


def tls_web_protocol(
    applications: Any, application_id: str, tls_enabled_default: Any
) -> str:
    """Return 'https' if effective TLS enabled else 'http'."""
    return (
        "https"
        if tls_enabled(applications, application_id, tls_enabled_default)
        else "http"
    )


def tls_web_port(
    applications: Any, application_id: str, tls_enabled_default: Any
) -> int:
    """Return 443 if effective TLS enabled else 80."""
    return 443 if tls_enabled(applications, application_id, tls_enabled_default) else 80


def tls_websocket_protocol(
    applications: Any, application_id: str, tls_enabled_default: Any
) -> str:
    """Return 'wss' if effective TLS enabled else 'ws'."""
    return (
        "wss"
        if tls_enabled(applications, application_id, tls_enabled_default)
        else "ws"
    )


class FilterModule(object):
    def filters(self) -> dict[str, Any]:
        return {
            "tls_enabled": tls_enabled,
            "tls_mode": tls_mode,
            "tls_san": tls_san,
            "tls_le_name": tls_le_name,
            "tls_web_protocol": tls_web_protocol,
            "tls_web_port": tls_web_port,
            "tls_websocket_protocol": tls_websocket_protocol,
        }
