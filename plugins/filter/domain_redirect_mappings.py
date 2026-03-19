from ansible.errors import AnsibleFilterError
from module_utils.entity_name_utils import get_entity_name


class FilterModule(object):
    def filters(self):
        return {"domain_mappings": self.domain_mappings}

    def domain_mappings(self, apps, primary_domain, auto_build_alias):
        """
        Build a flat list of redirect mappings for all apps:
          - source: each alias domain
          - target: the first canonical domain
        Skip mappings where source == target, since they make no sense.

        IMPORTANT:
        - If auto_build_alias is False, do NOT automatically add the default alias
          (<entity>.<primary_domain>) unless it is explicitly configured in aliases.
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

        def default_domain(app_id: str, primary: str):
            subdomain = get_entity_name(app_id)
            return f"{subdomain}.{primary}"

        # 1) Compute canonical domains per app (always as a list)
        canonical_map = {}
        for app_id, cfg in apps.items():
            domains_cfg = cfg.get("server", {}).get("domains", {})
            entry = domains_cfg.get("canonical")
            if entry is None:
                canonical_map[app_id] = [default_domain(app_id, primary_domain)]
            elif isinstance(entry, dict):
                canonical_map[app_id] = list(entry.values())
            elif isinstance(entry, list):
                canonical_map[app_id] = list(entry)
            else:
                raise AnsibleFilterError(
                    f"Unexpected type for 'server.domains.canonical' in application '{app_id}': {type(entry).__name__}"
                )

        # 2) Compute alias domains per app
        alias_map = {}
        for app_id, cfg in apps.items():
            domains_cfg = cfg.get("server", {}).get("domains", {})
            if domains_cfg is None:
                alias_map[app_id] = []
                continue

            default = default_domain(app_id, primary_domain)

            # If domains_cfg is explicitly an empty dict, that used to mean:
            # "use the default domain". But that is an auto-build behavior and
            # must be gated by auto_build_alias.
            if isinstance(domains_cfg, dict) and not domains_cfg:
                alias_map[app_id] = [default] if auto_build_alias else []
                continue

            aliases = parse_entry(domains_cfg, "aliases", app_id) or []
            has_aliases = "aliases" in domains_cfg
            has_canonical = "canonical" in domains_cfg

            if has_aliases:
                # ONLY auto-add default alias when enabled.
                # If the user set aliases: [], they likely want "no aliases".
                if auto_build_alias and default not in aliases:
                    aliases.append(default)
            elif has_canonical:
                # If canonical exists but aliases key does not, we may auto-add
                # the default alias when enabled (and only if it isn't already canonical).
                canon = canonical_map.get(app_id, [])
                if default not in canon and default not in aliases and auto_build_alias:
                    aliases.append(default)

            alias_map[app_id] = aliases

        # 3) Build flat list of {source, target} entries,
        #    skipping self-mappings
        mappings = []
        for app_id, sources in alias_map.items():
            canon_list = canonical_map.get(app_id, [])
            target = (
                canon_list[0] if canon_list else default_domain(app_id, primary_domain)
            )
            for src in sources:
                if src == target:
                    # skip self-redirects
                    continue
                mappings.append({"source": src, "target": target})

        return mappings
