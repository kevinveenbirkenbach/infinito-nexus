from ansible.errors import AnsibleFilterError
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.entity_name_utils import get_entity_name

class FilterModule(object):
    def filters(self):
        return {'canonical_domains_map': self.canonical_domains_map}

    def canonical_domains_map(self, apps, PRIMARY_DOMAIN):
        """
        Maps applications to their canonical domains, checking for conflicts 
        and ensuring all domains are valid and unique across applications.
        """
        result = {}
        seen_domains = {}

        for app_id, cfg in apps.items():
            if app_id.startswith((
                    "web-",
                    "svc-db-"   # Database services can also be exposed to the internet. It is just listening to the port, but the domain is used for port mapping
                    )):
                if not isinstance(cfg, dict):
                    raise AnsibleFilterError(
                    f"Invalid configuration for application '{app_id}': "
                    f"expected a dict, got {cfg!r}"
                )
                
                domains_cfg = cfg.get('server',{}).get('domains',{})
                if not domains_cfg or 'canonical' not in domains_cfg:
                    self._add_default_domain(app_id, PRIMARY_DOMAIN, seen_domains, result)
                    continue

                canonical_domains = domains_cfg['canonical']
                self._process_canonical_domains(app_id, canonical_domains, seen_domains, result)

        return result

    def _add_default_domain(self, app_id, PRIMARY_DOMAIN, seen_domains, result):
        """
        Add the default domain for an application if no canonical domains are defined.
        Ensures the domain is unique across applications.
        """
        entity_name = get_entity_name(app_id)
        default_domain = f"{entity_name}.{PRIMARY_DOMAIN}"
        if default_domain in seen_domains:
            raise AnsibleFilterError(
                f"Domain '{default_domain}' is already configured for "
                f"'{seen_domains[default_domain]}' and '{app_id}'"
            )
        seen_domains[default_domain] = app_id
        result[app_id] = [default_domain]

    def _process_canonical_domains(self, app_id, canonical_domains, seen_domains, result):
        """
        Process the canonical domains for an application, handling both lists and dicts,
        and ensuring each domain is unique.
        """
        if isinstance(canonical_domains, dict):
            self._process_canonical_domains_dict(app_id, canonical_domains, seen_domains, result)
        elif isinstance(canonical_domains, list):
            self._process_canonical_domains_list(app_id, canonical_domains, seen_domains, result)
        else:
            raise AnsibleFilterError(
                f"Unexpected type for 'server.domains.canonical' in application '{app_id}': "
                f"{type(canonical_domains).__name__}"
            )

    def _process_canonical_domains_dict(self, app_id, domains_dict, seen_domains, result):
        """
        Process a dictionary of canonical domains for an application.
        """
        for name, domain in domains_dict.items():
            self._validate_and_check_domain(app_id, domain, seen_domains)
        result[app_id] = domains_dict.copy()

    def _process_canonical_domains_list(self, app_id, domains_list, seen_domains, result):
        """
        Process a list of canonical domains for an application.
        """
        for domain in domains_list:
            self._validate_and_check_domain(app_id, domain, seen_domains)
        result[app_id] = list(domains_list)

    def _validate_and_check_domain(self, app_id, domain, seen_domains):
        """
        Validate the domain and check if it has already been assigned to another application.
        """
        if not isinstance(domain, str) or not domain.strip():
            raise AnsibleFilterError(
                f"Invalid domain entry in 'canonical' for application '{app_id}': {domain!r}"
            )
        if domain in seen_domains:
            raise AnsibleFilterError(
                f"Domain '{domain}' is already configured for '{seen_domains[domain]}' and '{app_id}'"
            )
        seen_domains[domain] = app_id
