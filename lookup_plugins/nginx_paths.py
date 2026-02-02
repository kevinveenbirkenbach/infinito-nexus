# lookup_plugins/nginx_paths.py
#
# Resolve nginx path configuration (lowercase keys) and (optionally) a domain-specific
# server config path placed under:
#
#   <servers_dir>/<protocol>/<domain>.conf
#
# Protocol resolution:
# - Default: resolved via tls_resolve:
#     lookup('tls_resolve', domain, want='protocols.web') -> "http" or "https"
# - Override: pass protocol=... to override ONLY the file path resolution for files.domain
#     lookup('nginx_paths', domain, protocol='http', want='files.domain')
#
# Base paths are read from applications using get_app_conf() (proxy app):
#   - docker.volumes.www
#   - docker.volumes.nginx
#
# Usage:
#   lookup('nginx_paths')
#   lookup('nginx_paths', 'example.com')
#   lookup('nginx_paths', 'example.com', want='files.domain')
#   lookup('nginx_paths', 'example.com', protocol='http', want='files.domain')
#
# New:
# - directories.ensure: list of {"path": "...", "mode": "0755"/"0700"} for host directory creation
#   This allows creating all required host dirs with a single Ansible task.
# - directories.configuration.http_includes: directories to include in nginx http{} via "*.conf"
#
# Notes:
# - Output keys are lowercase.
# - Domain-specific keys/files.domain exist ONLY if a domain term is passed.
# - If protocol override is passed without a domain, it is ignored.
# - directories.data.well_known is a container path and is intentionally NOT included in directories.ensure.

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.plugins.loader import lookup_loader

from module_utils.config_utils import get_app_conf
from module_utils.tls_common import as_str, require, want_get


def _join(*parts: Any) -> str:
    cleaned = [str(p).strip() for p in parts if str(p).strip()]
    return os.path.join(*cleaned) if cleaned else ""


def _ensure_trailing_slash(p: str) -> str:
    p = p.strip()
    if not p:
        return p
    return p if p.endswith("/") else p + "/"


def _normalize_protocol(value: str) -> str:
    v = as_str(value).strip().lower()
    if v in ("http", "https"):
        return v
    raise AnsibleError(
        f"nginx_paths: invalid protocol override '{value}' (expected http|https)"
    )


def _dir_spec(path: str, mode: str) -> Dict[str, str]:
    path = as_str(path).strip()
    mode = as_str(mode).strip()
    if not path:
        raise AnsibleError("nginx_paths: empty path in directories.ensure")
    if mode not in ("0700", "0755"):
        raise AnsibleError(
            f"nginx_paths: invalid mode '{mode}' in directories.ensure (expected 0700|0755)"
        )
    return {"path": path, "mode": mode}


def _resolve_protocol_via_tls_resolve(
    *,
    domain: str,
    variables: dict,
    loader: Any,
    templar: Any,
) -> str:
    """
    Resolve protocols.web using the tls_resolve lookup directly (no templar.template()).
    This avoids contexts where templar returns the lookup expression unchanged.
    """
    try:
        tls_lookup = lookup_loader.get("tls_resolve", loader=loader, templar=templar)
    except Exception as exc:
        raise AnsibleError(
            f"nginx_paths: failed to load tls_resolve lookup: {exc}"
        ) from exc

    try:
        protocol = tls_lookup.run([domain], variables=variables, want="protocols.web")[
            0
        ]
    except TypeError:
        protocol = tls_lookup.run([domain], variables=variables)[0]

    protocol_s = as_str(protocol).strip().lower()
    if protocol_s not in ("http", "https"):
        raise AnsibleError(
            f"nginx_paths: unexpected protocol '{protocol_s}' for domain '{domain}'"
        )
    return protocol_s


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}
        terms = terms or []

        # Accept: 0 or 1 term (optional domain)
        if len(terms) > 1:
            raise AnsibleError(
                "nginx_paths: accepts at most one term (optional domain)"
            )

        domain = as_str(terms[0]).strip() if terms else ""

        # Required inputs
        applications = require(variables, "applications", dict)

        # Source-of-truth application for proxy/openresty mounts
        proxy_app_id = as_str(kwargs.get("proxy_app_id", "svc-prx-openresty")).strip()
        if not proxy_app_id:
            raise AnsibleError("nginx_paths: proxy_app_id is empty")

        # Read base mount paths from the proxy app config
        www_dir = get_app_conf(
            applications, proxy_app_id, "docker.volumes.www", strict=True
        )
        nginx_dir = get_app_conf(
            applications, proxy_app_id, "docker.volumes.nginx", strict=True
        )

        www_dir = _ensure_trailing_slash(as_str(www_dir))
        nginx_dir = _ensure_trailing_slash(as_str(nginx_dir))

        # Derived directories (match your structure)
        conf_dir = _ensure_trailing_slash(_join(nginx_dir, "conf.d"))
        global_dir = _ensure_trailing_slash(_join(conf_dir, "global"))
        servers_dir = _ensure_trailing_slash(_join(conf_dir, "servers"))
        servers_http_dir = _ensure_trailing_slash(_join(servers_dir, "http"))
        servers_https_dir = _ensure_trailing_slash(_join(servers_dir, "https"))
        maps_dir = _ensure_trailing_slash(_join(conf_dir, "maps"))
        streams_dir = _ensure_trailing_slash(_join(conf_dir, "streams"))

        data_html_dir = _ensure_trailing_slash(_join(www_dir, "public_html"))
        data_files_dir = _ensure_trailing_slash(_join(www_dir, "public_files"))
        data_cdn_dir = _ensure_trailing_slash(_join(www_dir, "public_cdn"))
        data_global_dir = _ensure_trailing_slash(_join(www_dir, "global"))

        cache_general_dir = "/tmp/cache_nginx_general/"
        cache_image_dir = "/tmp/cache_nginx_image/"

        ensure: List[Dict[str, str]] = [
            _dir_spec(nginx_dir, "0755"),
            _dir_spec(conf_dir, "0755"),
            _dir_spec(global_dir, "0755"),
            _dir_spec(servers_dir, "0755"),
            _dir_spec(servers_http_dir, "0755"),
            _dir_spec(servers_https_dir, "0755"),
            _dir_spec(maps_dir, "0755"),
            _dir_spec(streams_dir, "0755"),
            _dir_spec(www_dir, "0755"),
            _dir_spec(data_html_dir, "0755"),
            _dir_spec(data_files_dir, "0755"),
            _dir_spec(data_cdn_dir, "0755"),
            _dir_spec(data_global_dir, "0755"),
            _dir_spec(cache_general_dir, "0700"),
            _dir_spec(cache_image_dir, "0700"),
        ]

        resolved: Dict[str, Any] = {
            "files": {
                "configuration": _join(nginx_dir, "nginx.conf"),
            },
            "directories": {
                "configuration": {
                    "base": conf_dir,
                    "global": global_dir,
                    "servers": servers_dir,
                    "maps": maps_dir,
                    "streams": streams_dir,
                    "http_includes": [
                        global_dir,
                        maps_dir,
                        servers_http_dir,
                        servers_https_dir,
                    ],
                },
                "data": {
                    "www": www_dir,
                    "well_known": "/usr/share/nginx/well-known/",
                    "html": data_html_dir,
                    "files": data_files_dir,
                    "cdn": data_cdn_dir,
                    "global": data_global_dir,
                },
                "cache": {
                    "general": cache_general_dir,
                    "image": cache_image_dir,
                },
                "ensure": ensure,
                "ensure_paths": [d["path"] for d in ensure],
            },
            "user": "http",
        }

        # Domain-specific: choose servers/http or servers/https
        if domain:
            protocol_override = kwargs.get("protocol", None)

            if protocol_override is None or as_str(protocol_override).strip() == "":
                protocol = _resolve_protocol_via_tls_resolve(
                    domain=domain,
                    variables=variables,
                    loader=getattr(self, "_loader", None),
                    templar=getattr(self, "_templar", None),
                )
            else:
                protocol = _normalize_protocol(protocol_override)

            domain_conf = _join(servers_dir, protocol, f"{domain}.conf")

            resolved["domain"] = {
                "name": domain,
                "protocol": protocol,
                "protocol_overridden": protocol_override is not None
                and as_str(protocol_override).strip() != "",
            }
            resolved["files"]["domain"] = domain_conf

        want = as_str(kwargs.get("want", "")).strip()
        if want:
            return [want_get(resolved, want)]

        return [resolved]
