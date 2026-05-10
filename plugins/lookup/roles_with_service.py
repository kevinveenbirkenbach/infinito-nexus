"""Lookup plugin: enumerate consumer roles for a given service.

Usage::

    {{ lookup('roles_with_service', 'dashboard') | to_json }}

Returns a sorted list of dicts ``[{id, canonical_domain}, …]``, one per
role whose merged applications config declares ``services.<service>.{
enabled, shared}`` as truthy AND that exposes a canonical domain.

Used by the SPOT-owner specs (web-app-{dashboard, prometheus, matomo})
to render a per-consumer manifest into ``templates/playwright.env.j2``.
The provider's ``files/playwright.spec.js`` then parameterises one
assertion per consumer over that manifest, owning the cross-service
reachability assertion in one place.

The lookup reuses ``get_merged_applications`` (the same helper
``lookup('applications', ...)`` uses) so the data is already rendered
against the inventory's ``group_names`` at runtime — no template-side
``for`` loops or filter logic required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.cache.applications import get_merged_applications

if TYPE_CHECKING:
    from collections.abc import Sequence


def _resolve_canonical_domain(app_config: dict[str, Any]) -> str:
    server = app_config.get("server")
    if not isinstance(server, dict):
        return ""
    domains = server.get("domains")
    if not isinstance(domains, dict):
        return ""
    canonical = domains.get("canonical")
    if isinstance(canonical, list) and canonical:
        first = canonical[0]
        return str(first) if first else ""
    if isinstance(canonical, str):
        return canonical
    return ""


class LookupModule(LookupBase):
    def run(
        self,
        terms: Sequence[Any] | None,
        variables: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        terms = list(terms or [])
        if len(terms) != 1:
            raise AnsibleError(
                "roles_with_service: expected exactly one term — the "
                "service name (e.g. 'dashboard', 'prometheus', 'matomo')."
            )
        service_name = str(terms[0]).strip()
        if not service_name:
            raise AnsibleError("roles_with_service: service name must be non-empty")

        applications = get_merged_applications(
            variables=variables
            or getattr(self._templar, "available_variables", {})
            or {},
            roles_dir=kwargs.get("roles_dir"),
            templar=getattr(self, "_templar", None),
        )

        results: list[dict[str, str]] = []
        for role_id, app_config in applications.items():
            if not isinstance(app_config, dict):
                continue
            services = app_config.get("services")
            if not isinstance(services, dict):
                continue
            block = services.get(service_name)
            if not isinstance(block, dict):
                continue
            if not bool(block.get("enabled")):
                continue
            if not bool(block.get("shared")):
                continue
            canonical = _resolve_canonical_domain(app_config)
            if not canonical:
                continue
            results.append({"id": str(role_id), "canonical_domain": canonical})

        results.sort(key=lambda r: r["id"])
        return [results]
