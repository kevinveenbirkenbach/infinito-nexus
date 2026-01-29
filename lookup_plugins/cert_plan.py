# lookup_plugins/cert_plan.py
#
# Certificate planning lookup for Infinito.Nexus:
# - Computes certificate file paths (cert/key/ca)
# - Computes effective SAN list (domains.san)
# - Supports self-signed scope: "app" | "global"
#
# See module_utils/tls_common.py for shared resolution logic.

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.tls_common import (
    AVAILABLE_FLAVORS,
    as_str,
    collect_domains_for_app,
    collect_domains_global,
    override_san_list,
    require,
    resolve_enabled,
    resolve_le_name,
    resolve_mode,
    resolve_term,
    uniq_preserve,
    want_get,
)

LE_FULLCHAIN = "fullchain.pem"
LE_PRIVKEY = "privkey.pem"


def _join(*parts: Any) -> str:
    cleaned = [str(p).strip() for p in parts if str(p).strip()]
    return os.path.join(*cleaned) if cleaned else ""


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        if not terms or len(terms) != 1:
            raise AnsibleError(
                "cert_plan: exactly one term required (domain or application_id)"
            )

        term = as_str(terms[0])
        if not term:
            raise AnsibleError("cert_plan: term is empty")

        def _looks_like_jinja(s: str) -> bool:
            return ("{{" in s) or ("{%" in s)

        def _build_render_context() -> tuple[dict, str]:
            """
            Build a robust context for rendering Jinja-in-strings.

            We intentionally do NOT rely on Ansible's Templar here because in some
            lookup evaluation contexts it can silently keep Jinja markers untouched.
            """
            ctx: dict = {}
            if isinstance(variables, dict):
                ctx.update(variables)

            inv_host = ""
            if isinstance(variables, dict):
                inv_host = as_str(variables.get("inventory_hostname", "")).strip()

            hostvars = (
                variables.get("hostvars") if isinstance(variables, dict) else None
            )
            if inv_host and isinstance(hostvars, dict):
                hv = hostvars.get(inv_host)
                if isinstance(hv, dict):
                    # hostvars should win for things like SOFTWARE_NAME
                    ctx.update(hv)

            return ctx, inv_host

        def _render_jinja2_strict(
            raw: str, *, ctx: dict, inv_host: str, var_name: str
        ) -> str:
            """
            Render using plain Jinja2 with StrictUndefined so missing vars fail hard.
            This ensures we never leak "{{ ... }}" into generated configs.
            """
            if not _looks_like_jinja(raw):
                return raw

            try:
                from jinja2 import Environment, StrictUndefined
            except Exception as exc:
                raise AnsibleError(
                    f"cert_plan: cannot import jinja2 to expand {var_name}. Error: {exc}"
                ) from exc

            env = Environment(undefined=StrictUndefined)
            try:
                rendered = env.from_string(raw).render(ctx)
            except Exception as exc:
                raise AnsibleError(
                    f"cert_plan: failed to render {var_name} via strict Jinja2. "
                    f"inventory_hostname='{inv_host}'. Raw: {raw}. Error: {exc}"
                ) from exc

            rendered_s = as_str(rendered)

            if _looks_like_jinja(rendered_s):
                raise AnsibleError(
                    f"cert_plan: {var_name} did not fully expand (still contains Jinja markers). "
                    f"inventory_hostname='{inv_host}'. Raw: {raw} | Rendered: {rendered_s}."
                )

            return rendered_s

        def _render_var(value: Any, *, var_name: str) -> str:
            raw = as_str(value)
            if not raw:
                return raw

            if not _looks_like_jinja(raw):
                return raw

            ctx, inv_host = _build_render_context()
            return _render_jinja2_strict(
                raw, ctx=ctx, inv_host=inv_host, var_name=var_name
            )

        domains = require(variables, "domains", dict)
        applications = require(variables, "applications", dict)
        enabled_default = require(variables, "TLS_ENABLED", (bool, int))
        mode_default = as_str(require(variables, "TLS_MODE", str))
        le_live = ""

        if mode_default not in AVAILABLE_FLAVORS:
            raise AnsibleError(
                f"cert_plan: TLS_MODE must be one of {sorted(AVAILABLE_FLAVORS)}, got '{mode_default}'"
            )

        forced_mode = as_str(kwargs.get("mode", "auto")).lower()
        app_id, primary_domain = resolve_term(
            term, domains=domains, forced_mode=forced_mode, err_prefix="cert_plan"
        )

        app = applications.get(app_id, {})
        if not isinstance(app, dict):
            app = {}

        enabled = resolve_enabled(app, bool(enabled_default))
        mode = resolve_mode(app, enabled, mode_default, err_prefix="cert_plan")

        cert_file = ""
        key_file = ""
        ca_file = ""
        san_domains: list[str] = []
        cert_id = ""
        scope = "app"

        if mode == "off":
            pass

        elif mode == "letsencrypt":
            le_live_raw = require(variables, "LETSENCRYPT_LIVE_PATH", str)
            le_live = _render_var(le_live_raw, var_name="LETSENCRYPT_LIVE_PATH")

            le_name = resolve_le_name(app, primary_domain)
            cert_id = le_name

            cert_file = _join(le_live, le_name, LE_FULLCHAIN)
            key_file = _join(le_live, le_name, LE_PRIVKEY)

            all_domains = collect_domains_for_app(
                domains, app_id, err_prefix="cert_plan"
            )
            all_domains = (
                uniq_preserve([primary_domain] + all_domains)
                if all_domains
                else [primary_domain]
            )

            san_override = override_san_list(app)
            if san_override is None:
                san_domains = all_domains[:]
            else:
                san_domains = uniq_preserve([primary_domain] + san_override)

        elif mode == "self_signed":
            ss_base_raw = require(variables, "TLS_SELFSIGNED_BASE_PATH", str)
            ss_base = _render_var(ss_base_raw, var_name="TLS_SELFSIGNED_BASE_PATH")

            ss_scope = as_str(variables.get("TLS_SELFSIGNED_SCOPE")).lower()
            if ss_scope not in {"app", "global"}:
                raise AnsibleError(
                    "cert_plan: TLS_SELFSIGNED_SCOPE must be 'app' or 'global'"
                )

            scope = ss_scope

            if ss_scope == "global":
                cert_id = "_global"
                cert_file = _join(ss_base, cert_id, LE_FULLCHAIN)
                key_file = _join(ss_base, cert_id, LE_PRIVKEY)

                san_domains = collect_domains_global(domains)
                san_domains = (
                    uniq_preserve([primary_domain] + san_domains)
                    if primary_domain
                    else san_domains
                )
            else:
                cert_id = app_id
                cert_file = _join(ss_base, app_id, primary_domain, LE_FULLCHAIN)
                key_file = _join(ss_base, app_id, primary_domain, LE_PRIVKEY)

                all_domains = collect_domains_for_app(
                    domains, app_id, err_prefix="cert_plan"
                )
                all_domains = (
                    uniq_preserve([primary_domain] + all_domains)
                    if all_domains
                    else [primary_domain]
                )

                san_override = override_san_list(app)
                if san_override is None:
                    san_domains = all_domains[:]
                else:
                    san_domains = uniq_preserve([primary_domain] + san_override)

        else:
            raise AnsibleError(f"cert_plan: unsupported mode '{mode}'")

        resolved: Dict[str, Any] = {
            "application_id": app_id,
            "domain": primary_domain,
            "enabled": enabled,
            "mode": mode,
            "scope": scope,
            "cert_id": cert_id,
            "domains": {"san": san_domains},
            "files": {"cert": cert_file, "key": key_file, "ca": ca_file},
        }

        want = as_str(kwargs.get("want", ""))
        if want:
            return [want_get(resolved, want)]
        return [resolved]
