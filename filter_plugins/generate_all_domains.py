from ansible.errors import AnsibleFilterError

class FilterModule(object):
    def filters(self):
        return {'generate_all_domains': self.generate_all_domains}

    def generate_all_domains(self, domains_dict, include_www:bool=True):
        """
        Transform a dict of domains (values: str, list, dict) into a flat list,
        optionally add 'www.' prefixes, dedupe and sort alphabetically.
        """
        # lokaler Helfer zum Flatten
        def _flatten(domains):
            flat = []
            for v in (domains or {}).values():
                if isinstance(v, str):
                    flat.append(v)
                elif isinstance(v, list):
                    flat.extend(v)
                elif isinstance(v, dict):
                    flat.extend(v.values())
            return flat

        try:
            flat = _flatten(domains_dict)
            if include_www:
                original = list(flat)
                flat.extend([f"www.{d}" for d in original])
            return sorted(set(flat))
        except Exception as exc:
            raise AnsibleFilterError(f"generate_all_domains failed: {exc}")
