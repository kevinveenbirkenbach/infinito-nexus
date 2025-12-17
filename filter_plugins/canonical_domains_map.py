from ansible.errors import AnsibleFilterError
import os
from module_utils.entity_name_utils import get_entity_name
from module_utils.role_dependency_resolver import RoleDependencyResolver
from typing import Iterable


class FilterModule(object):
    def filters(self):
        return {"canonical_domains_map": self.canonical_domains_map}

    def canonical_domains_map(
        self,
        apps,
        PRIMARY_DOMAIN,
        *,
        recursive: bool = False,
        roles_base_dir: str | None = None,
        seed: Iterable[str] | None = None,
    ):
        """
        Build { app_id: [canonical domains...] }.

        Rekursiv werden nur include_role, import_role und meta/main.yml:dependencies verfolgt.
        'run_after' wird hier absichtlich ignoriert.
        """
        if not isinstance(apps, dict):
            raise AnsibleFilterError(
                f"'apps' must be a dict, got {type(apps).__name__}"
            )

        app_keys = set(apps.keys())
        seed_keys = set(seed) if seed is not None else app_keys

        if recursive:
            roles_base_dir = roles_base_dir or os.path.join(os.getcwd(), "roles")
            if not os.path.isdir(roles_base_dir):
                raise AnsibleFilterError(
                    f"roles_base_dir '{roles_base_dir}' not found or not a directory."
                )

            resolver = RoleDependencyResolver(roles_base_dir)
            discovered_roles = resolver.resolve_transitively(
                start_roles=seed_keys,
                resolve_include_role=True,
                resolve_import_role=True,
                resolve_dependencies=True,
                resolve_run_after=False,
                max_depth=None,
            )
            # all discovered roles that actually have config entries in `apps`
            target_apps = discovered_roles & app_keys
        else:
            target_apps = seed_keys

        result = {}
        seen_domains = {}

        for app_id in sorted(target_apps):
            cfg = apps.get(app_id)
            if cfg is None:
                continue
            if not str(app_id).startswith(("web-", "svc-db-")):
                continue
            if not isinstance(cfg, dict):
                raise AnsibleFilterError(
                    f"Invalid configuration for application '{app_id}': expected dict, got {cfg!r}"
                )

            domains_cfg = cfg.get("server", {}).get("domains", {})
            if not domains_cfg or "canonical" not in domains_cfg:
                self._add_default_domain(app_id, PRIMARY_DOMAIN, seen_domains, result)
                continue

            canonical_domains = domains_cfg["canonical"]
            self._process_canonical_domains(
                app_id, canonical_domains, seen_domains, result
            )

        return result

    def _add_default_domain(self, app_id, PRIMARY_DOMAIN, seen_domains, result):
        entity_name = get_entity_name(app_id)
        default_domain = f"{entity_name}.{PRIMARY_DOMAIN}"
        if default_domain in seen_domains:
            raise AnsibleFilterError(
                f"Domain '{default_domain}' is already configured for "
                f"'{seen_domains[default_domain]}' and '{app_id}'"
            )
        seen_domains[default_domain] = app_id
        result[app_id] = [default_domain]

    def _process_canonical_domains(
        self, app_id, canonical_domains, seen_domains, result
    ):
        if isinstance(canonical_domains, dict):
            for _, domain in canonical_domains.items():
                self._validate_and_check_domain(app_id, domain, seen_domains)
            result[app_id] = canonical_domains.copy()
        elif isinstance(canonical_domains, list):
            for domain in canonical_domains:
                self._validate_and_check_domain(app_id, domain, seen_domains)
            result[app_id] = list(canonical_domains)
        else:
            raise AnsibleFilterError(
                f"Unexpected type for 'server.domains.canonical' in application '{app_id}': "
                f"{type(canonical_domains).__name__}"
            )

    def _validate_and_check_domain(self, app_id, domain, seen_domains):
        if not isinstance(domain, str) or not domain.strip():
            raise AnsibleFilterError(
                f"Invalid domain entry in 'canonical' for application '{app_id}': {domain!r}"
            )
        if domain in seen_domains:
            raise AnsibleFilterError(
                f"Domain '{domain}' is already configured for '{seen_domains[domain]}' and '{app_id}'"
            )
        seen_domains[domain] = app_id
