# filter_plugins/tls.py
#
# KISS TLS resolution helpers for Infinito.Nexus:
# - TLS_ENABLED is only a host default
# - applications[app_id].server.tls.* overrides per app
#
# Exposed filters:
# - tls_enabled(applications, app_id, default_enabled=True) -> bool
# - tls_mode(applications, app_id, default_enabled=True, default_flavor="letsencrypt") -> str
# - tls_san(applications, app_id, default=None) -> list[str]
# - tls_le_name(applications, app_id, default="") -> str

from __future__ import annotations
from typing import Any


_AVAILABLE_FLAVORS = {"letsencrypt", "self_signed"}


def _get_path(d: Any, path: str, default: Any = None) -> Any:
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
    applications: Any, application_id: str, default_enabled: Any = True
) -> bool:
    """
    Effective TLS enabled flag:
    - applications[app].server.tls.enabled overrides
    - else fallback to default_enabled (TLS_ENABLED)
    """
    app = _get_app(applications, application_id)

    override = _get_path(app, "server.tls.enabled", default=None)

    if override is None:
        return bool(default_enabled)

    return bool(override)


def tls_mode(
    applications: Any,
    application_id: str,
    default_enabled: Any = True,
    default_flavor: str = "letsencrypt",
) -> str:
    """
    Effective TLS mode:
    - if tls is disabled -> "off"
    - else -> server.tls.flavor (default: default_flavor)
    """

    if not tls_enabled(applications, application_id, default_enabled):
        return "off"

    app = _get_app(applications, application_id)
    flavor = _get_path(app, "server.tls.flavor", default_flavor)

    if not isinstance(flavor, str) or not flavor.strip():
        flavor = default_flavor

    flavor = flavor.strip()

    if flavor not in _AVAILABLE_FLAVORS:
        flavor = default_flavor

    return flavor


def tls_san(applications: Any, application_id: str, default: Any = None) -> list[str]:
    """Return SAN list from server.tls.domains_san."""
    if default is None:
        default = []

    app = _get_app(applications, application_id)
    san = _get_path(app, "server.tls.domains_san", default)

    if san is None:
        return []

    if isinstance(san, list):
        return [str(x).strip() for x in san if str(x).strip()]

    if isinstance(san, str) and san.strip():
        return [san.strip()]

    return []


def tls_le_name(applications: Any, application_id: str, default: str = "") -> str:
    """Return Let's Encrypt cert name override."""
    app = _get_app(applications, application_id)
    name = _get_path(app, "server.tls.letsencrypt_cert_name", default)
    return str(name).strip() if name is not None else str(default).strip()


def tls_web_protocol(
    applications: Any, application_id: str, default_enabled: Any = True
) -> str:
    """Return 'https' if effective tls_enabled else 'http'."""
    return (
        "https"
        if tls_enabled(applications, application_id, default_enabled)
        else "http"
    )


def tls_web_port(
    applications: Any, application_id: str, default_enabled: Any = True
) -> int:
    """Return 443 if effective tls_enabled else 80."""
    return 443 if tls_enabled(applications, application_id, default_enabled) else 80


def tls_websocket_protocol(
    applications: Any, application_id: str, default_enabled: Any = True
) -> str:
    """Return 'wss' if effective tls_enabled else 'ws'."""
    return "wss" if tls_enabled(applications, application_id, default_enabled) else "ws"


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
