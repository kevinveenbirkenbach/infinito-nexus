# module_utils/domain_mapper.py
#
# SRP helper: Map a domain (canonical or alias) to an application_id by scanning
# applications[app_id].server.domains.{canonical,aliases}.
#
# Supports canonical/aliases being:
# - str
# - list
# - dict (possibly nested, like "web/api/view" variants)
#
# Note:
# This module does NOT template Jinja. It expects values to already
# be rendered at lookup runtime (usually true for Ansible variables).

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from ansible.errors import AnsibleError


def _norm_domain(value: Any) -> str:
    s = str(value).strip() if value is not None else ""
    return s.lower()


def _flatten_str_values(value: Any) -> List[str]:
    """
    Recursively flatten strings from value.
    Accepts str | list | dict | nested combinations.
    Returns list[str] preserving discovery order (best effort).
    """
    out: List[str] = []

    def walk(v: Any) -> None:
        if v is None:
            return
        if isinstance(v, str):
            s = v.strip()
            if s:
                out.append(s)
            return
        if isinstance(v, list):
            for item in v:
                walk(item)
            return
        if isinstance(v, dict):
            # For dicts we take values (keys are semantic like web/api/view)
            for vv in v.values():
                walk(vv)
            return
        # ignore other types silently (ints, bools, etc.)

    walk(value)
    return out


def iter_app_domains(app_conf: Any) -> Iterable[str]:
    """
    Yield all canonical + alias domains from an app config.

    Expected structure:
      applications[app_id].server.domains.canonical
      applications[app_id].server.domains.aliases
    """
    if not isinstance(app_conf, dict):
        return []

    server = app_conf.get("server", {})
    if not isinstance(server, dict):
        return []

    domains = server.get("domains", {})
    if not isinstance(domains, dict):
        return []

    canonical = domains.get("canonical", [])
    aliases = domains.get("aliases", [])

    result: List[str] = []
    result.extend(_flatten_str_values(canonical))
    result.extend(_flatten_str_values(aliases))
    return result


def build_domain_index(applications: Dict[str, Any]) -> Dict[str, str]:
    """
    Build a case-insensitive domain -> application_id index.
    If the same domain appears in multiple apps (case-insensitive), raises an error.
    """
    if not isinstance(applications, dict):
        raise AnsibleError("domain_mapper: applications must be a dict")

    index: Dict[str, str] = {}  # normalized domain -> app_id
    collisions: Dict[str, Set[str]] = {}

    for app_id, app_conf in applications.items():
        for d in iter_app_domains(app_conf):
            nd = _norm_domain(d)
            if not nd:
                continue

            if nd in index and index[nd] != app_id:
                collisions.setdefault(nd, set()).update({index[nd], app_id})
            else:
                index[nd] = app_id

    if collisions:
        parts = []
        for domain, apps in sorted(collisions.items(), key=lambda x: x[0]):
            parts.append(f"{domain}: {sorted(apps)}")
        raise AnsibleError(
            "domain_mapper: domain collision across applications (ambiguous mapping): "
            + "; ".join(parts)
        )

    return index


def resolve_app_id_for_domain(
    applications: Dict[str, Any],
    domain: str,
) -> Optional[str]:
    """
    Resolve application_id for a given domain (canonical or alias) by scanning
    applications[*].server.domains.

    Returns None if not found.
    """
    nd = _norm_domain(domain)
    if not nd:
        return None

    idx = build_domain_index(applications)
    return idx.get(nd)
