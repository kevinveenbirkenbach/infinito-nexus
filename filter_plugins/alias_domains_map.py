from ansible.errors import AnsibleFilterError

class FilterModule(object):
    def filters(self):
        return {'alias_domains_map': self.alias_domains_map}

    def alias_domains_map(self, apps, PRIMARY_DOMAIN):
        """
        Build a map of application IDs to their alias domains.

        - If no `domains` key → []  
        - If `domains` exists but is an empty dict → return the original cfg  
        - Explicit `aliases` are used (default appended if missing)  
        - If only `canonical` defined and it doesn't include default, default is added  
        - Invalid types raise AnsibleFilterError
        """
        def parse_entry(domains_cfg, key, app_id):
            if key not in domains_cfg:
                return None
            entry = domains_cfg[key]
            if isinstance(entry, dict):
                values = list(entry.values())
            elif isinstance(entry, list):
                values = entry
            else:
                raise AnsibleFilterError(
                    f"Unexpected type for 'domains.{key}' in application '{app_id}': {type(entry).__name__}"
                )
            for d in values:
                if not isinstance(d, str) or not d.strip():
                    raise AnsibleFilterError(
                        f"Invalid domain entry in '{key}' for application '{app_id}': {d!r}"
                    )
            return values

        def default_domain(app_id, primary):
            return f"{app_id}.{primary}"

        # 1) Precompute canonical domains per app (fallback to default)
        canonical_map = {}
        for app_id, cfg in apps.items():
            domains_cfg = cfg.get('server',{}).get('domains',{})
            entry = domains_cfg.get('canonical')
            if entry is None:
                canonical_map[app_id] = [default_domain(app_id, PRIMARY_DOMAIN)]
            elif isinstance(entry, dict):
                canonical_map[app_id] = list(entry.values())
            elif isinstance(entry, list):
                canonical_map[app_id] = list(entry)
            else:
                raise AnsibleFilterError(
                    f"Unexpected type for 'server.domains.canonical' in application '{app_id}': {type(entry).__name__}"
                )

        # 2) Build alias list per app
        result = {}
        for app_id, cfg in apps.items():
            domains_cfg = cfg.get('server',{}).get('domains')

            # no domains key → no aliases
            if domains_cfg is None:
                result[app_id] = []
                continue

            # empty domains dict → return the original cfg
            if isinstance(domains_cfg, dict) and not domains_cfg:
                result[app_id] = cfg
                continue

            # otherwise, compute aliases
            aliases = parse_entry(domains_cfg, 'aliases', app_id) or []
            default = default_domain(app_id, PRIMARY_DOMAIN)
            has_aliases = 'aliases' in domains_cfg
            has_canon   = 'canonical' in domains_cfg

            if has_aliases:
                if default not in aliases:
                    aliases.append(default)
            elif has_canon:
                canon = canonical_map.get(app_id, [])
                if default not in canon and default not in aliases:
                    aliases.append(default)

            result[app_id] = aliases

        return result