from ansible.errors import AnsibleFilterError
import ipaddress


def _validate(d: str) -> None:
    if not isinstance(d, str) or not d.strip() or d.startswith(".") or d.endswith(".") or ".." in d:
        raise AnsibleFilterError(f"Invalid domain: {d!r}")


def _depth(domain: str, apex: str) -> int:
    dl, al = domain.split("."), apex.split(".")
    if not domain.endswith(apex) or len(dl) <= len(al):
        return 0
    return len(dl) - len(al)


def _parent_of_child(domain: str, apex: str) -> str | None:
    """For a child like a.b.example.com return b.example.com; else None (needs depth >= 2)."""
    if not domain.endswith(apex):
        return None
    parts = domain.split(".")
    apex_len = len(apex.split("."))
    if len(parts) <= apex_len + 1:
        return None
    return ".".join(parts[1:])  # drop exactly the left-most label


def _flatten_domains(current_play_domains: dict) -> list[str]:
    """
    Accept CURRENT_PLAY_DOMAINS values as:
      - str
      - list/tuple/set[str]
      - dict -> recurse one level (values must be str or list-like[str])
    """
    if not isinstance(current_play_domains, dict):
        raise AnsibleFilterError("CURRENT_PLAY_DOMAINS must be a dict of {app_id: hostnames-or-structures}")

    hosts: list[str] = []

    def _add_any(x):
        if x is None:
            return
        if isinstance(x, str):
            hosts.append(x)
            return
        if isinstance(x, (list, tuple, set)):
            for i in x:
                if not isinstance(i, str):
                    raise AnsibleFilterError(f"Non-string hostname in list: {i!r}")
                hosts.append(i)
            return
        if isinstance(x, dict):
            for v in x.values():
                _add_any(v)
            return
        raise AnsibleFilterError(f"Unsupported CURRENT_PLAY_DOMAINS value type: {type(x).__name__}")

    for v in current_play_domains.values():
        _add_any(v)

    return sorted(set(hosts))


def _parents_from(domains: list[str], apex: str, *, min_child_depth: int, include_apex: bool) -> list[str]:
    _validate(apex)
    parents = set([apex]) if include_apex else set()
    for d in domains:
        _validate(d)
        if not d.endswith(apex):
            continue
        if _depth(d, apex) >= min_child_depth:
            p = _parent_of_child(d, apex)
            if p:
                parents.add(p)
    return sorted(parents)


def _relative_names(fqdns: list[str], apex: str) -> list[str]:
    """FQDN -> relative name; '' represents the apex."""
    _validate(apex)
    out: list[str] = []
    for d in fqdns:
        _validate(d)
        if not d.endswith(apex):
            continue
        if d == apex:
            out.append("")
        else:
            out.append(d[: -(len(apex) + 1)])  # strip ".apex"
    return sorted(set(out))


def _is_global(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except Exception:
        return False


def _build_cf_records(
    rel_parents: list[str],
    apex: str,
    *,
    ip4: str,
    ip6: str | None,
    ipv6_enabled: bool,
    proxied: bool,
    wildcard_children: bool,
    apex_wildcard: bool,
) -> list[dict]:
    if not isinstance(rel_parents, list):
        raise AnsibleFilterError("rel_parents must be list[str]")
    _validate(apex)
    if not ip4:
        raise AnsibleFilterError("ip4 required")

    records: list[dict] = []

    def _add_one(name: str, rtype: str, content: str):
        records.append({
            "zone": apex,
            "type": rtype,
            "name": name if name else "@",
            "content": content,
            "proxied": bool(proxied),
            "ttl": 1,
        })

    for rel in sorted(set(rel_parents)):
        # base (parent) host
        _add_one(rel, "A", str(ip4))
        if ipv6_enabled and ip6 and _is_global(str(ip6)):
            _add_one(rel, "AAAA", str(ip6))

        # wildcard children under the parent
        if rel and wildcard_children:
            wc = f"*.{rel}"
            _add_one(wc, "A", str(ip4))
            if ipv6_enabled and ip6 and _is_global(str(ip6)):
                _add_one(wc, "AAAA", str(ip6))

    # optional apex wildcard (*.example.com)
    if apex_wildcard:
        _add_one("*", "A", str(ip4))
        if ipv6_enabled and ip6 and _is_global(str(ip6)):
            _add_one("*", "AAAA", str(ip6))

    return records


def parent_build_records(
    current_play_domains: dict,
    apex: str,
    ip4: str,
    ip6: str | None = None,
    proxied: bool = False,
    explicit_domains: list[str] | None = None,
    include_apex: bool = True,
    min_child_depth: int = 2,
    wildcard_children: bool = True,
    include_apex_wildcard: bool = False,
    ipv6_enabled: bool = False,
) -> list[dict]:
    """
    Return Cloudflare A/AAAA records for:
      - each parent host ('' == apex),
      - optionally '*.parent' for wildcard children,
      - optionally '*.apex'.
    """
    # source domains
    if explicit_domains and len(explicit_domains) > 0:
        domains = sorted(set(explicit_domains))
    else:
        domains = _flatten_domains(current_play_domains)

    parents = _parents_from(domains, apex, min_child_depth=min_child_depth, include_apex=include_apex)
    rel_parents = _relative_names(parents, apex)

    return _build_cf_records(
        rel_parents,
        apex,
        ip4=ip4,
        ip6=ip6,
        ipv6_enabled=ipv6_enabled,
        proxied=proxied,
        wildcard_children=wildcard_children,
        apex_wildcard=include_apex_wildcard,
    )


class FilterModule(object):
    def filters(self):
        return {
            "parent_build_records": parent_build_records,
        }
