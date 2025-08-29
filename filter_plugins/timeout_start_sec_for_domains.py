from ansible.errors import AnsibleFilterError

class FilterModule(object):
    """
    Compute a max TimeoutStartSec for systemd services that iterate over many domains.
    The timeout scales with the number of unique domains (optionally including www.* clones)
    and is clamped between configurable min/max bounds.
    """

    def filters(self):
        return {
            "timeout_start_sec_for_domains": self.timeout_start_sec_for_domains,
        }

    def timeout_start_sec_for_domains(
        self,
        domains_dict,
        include_www=True,
        per_domain_seconds=25,
        overhead_seconds=30,
        min_seconds=120,
        max_seconds=3600,
    ):
        """
        Args:
            domains_dict (dict): Same structure you pass to generate_all_domains
                                 (values can be str | list[str] | dict[str,str]).
            include_www (bool):   If true, also count "www.<domain>" variants.
            per_domain_seconds (int): Budget per domain (default 25s).
            overhead_seconds (int):  Fixed overhead on top (default 30s).
            min_seconds (int):       Lower clamp (default 120s).
            max_seconds (int):       Upper clamp (default 3600s).

        Returns:
            int: TimeoutStartSec in seconds (integer).

        Raises:
            AnsibleFilterError: On invalid input types or unexpected failures.
        """
        try:
            if not isinstance(domains_dict, dict):
                raise AnsibleFilterError("Expected 'domains_dict' to be a dict.")

            # Local flatten similar to your generate_all_domains
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

            flat = _flatten(domains_dict)

            if include_www:
                # dedupe first so we don't generate duplicate www-variants
                base_unique = sorted(set(flat))
                www_variants = [f"www.{d}" for d in base_unique if not str(d).startswith("www.")]
                flat.extend(www_variants)

            unique_domains = sorted(set(flat))
            count = len(unique_domains)

            # Compute and clamp
            raw = overhead_seconds + per_domain_seconds * count
            clamped = max(min_seconds, min(max_seconds, int(raw)))
            return clamped

        except AnsibleFilterError:
            raise
        except Exception as exc:
            raise AnsibleFilterError(f"timeout_start_sec_for_domains failed: {exc}")
