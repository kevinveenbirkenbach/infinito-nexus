from typing import Iterable


class FilterModule(object):
    """Custom Jinja2 filters for LDAP related rendering."""

    def filters(self):
        return {
            "ldap_groups_filter": self.ldap_groups_filter,
        }

    def ldap_groups_filter(self, flavors, default="groupOfNames") -> str:
        """
        Build an LDAP objectClass filter for groups based on available flavors.

        Args:
            flavors: list/tuple/set of enabled flavors (e.g. ["groupOfNames","organizationalUnit"])
            default: fallback objectClass if nothing matches

        Returns:
            A *single-line* LDAP filter string suitable for JSON, e.g.:
            (|(objectClass=groupOfNames)(objectClass=organizationalUnit))

        Rules:
          - If both groupOfNames and organizationalUnit are present -> OR them.
          - If one of them is present -> use that one.
          - Otherwise -> use `default`.
        """
        if flavors is None:
            flavors = []
        if isinstance(flavors, str):
            # be forgiving if someone passes a comma-separated string
            flavors = [f.strip() for f in flavors.split(",") if f.strip()]
        if not isinstance(flavors, Iterable):
            raise ValueError(
                "ldap_groups_filter: 'flavors' must be an iterable or comma-separated string"
            )

        have_gon = "groupOfNames" in flavors
        have_ou = "organizationalUnit" in flavors

        if have_gon and have_ou:
            classes = ["groupOfNames", "organizationalUnit"]
            return f"(|{''.join(f'(objectClass={c})' for c in classes)})"
        if have_gon:
            return "(objectClass=groupOfNames)"
        if have_ou:
            return "(objectClass=organizationalUnit)"
        # fallback
        return f"(objectClass={default})"
