from ansible.errors import AnsibleFilterError

class FilterModule(object):
    """
    Custom filters for redirect domain mappings
    """

    def filters(self):
        return {
            "add_redirect_if_group": self.add_redirect_if_group,
        }

    @staticmethod
    def add_redirect_if_group(redirect_list, group, source, target, group_names):
        """
        Append {"source": source, "target": target} to *redirect_list*
        **only** if *group* is contained in *group_names*.

        Usage in Jinja:
          {{ redirect_list
               | add_redirect_if_group('lam',
                                       'ldap.' ~ PRIMARY_DOMAIN,
                                       domains | get_domain('web-app-lam'),
                                       group_names) }}
        """
        try:
            # Make a copy so we don’t mutate the original list in place
            redirects = list(redirect_list)

            if group in group_names:
                redirects.append({"source": source, "target": target})

            return redirects

        except Exception as exc:
            raise AnsibleFilterError(f"add_redirect_if_group failed: {exc}")
