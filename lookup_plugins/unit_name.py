# lookup_plugins/unit_name.py
#
# Ansible lookup plugin to build versioned systemd unit names.
#
# Target format:
#   <systemctl_id>.<version>.<software_domain><suffix>
#
# Examples:
#   lookup('unit_name', 'svc-foo')                       -> svc-foo.1.2.3.infinito.nexus.service
#   lookup('unit_name', 'svc-foo', suffix='.timer')      -> svc-foo.1.2.3.infinito.nexus.timer
#   lookup('unit_name', 'alarm@')                        -> alarm.1.2.3.infinito.nexus@.service
#
# Requirements:
# - SOFTWARE_DOMAIN must be available in vars (inventory/group_vars/role vars).
# - Version is read via lookup('version') (your existing version lookup plugin).

from __future__ import annotations

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError


def _normalize_suffix(suffix) -> str:
    """
    Normalize suffix input to a systemd unit suffix string:
    - None / "" -> ".service"
    - False -> "" (no suffix)
    - "service" -> ".service"
    - ".timer" -> ".timer"
    """
    if suffix is False:
        return ""
    if suffix is None or str(suffix).strip() == "":
        return ".service"

    sfx = str(suffix).strip().lower()
    if not sfx.startswith("."):
        sfx = "." + sfx
    return sfx


def _lower_required(value, name: str) -> str:
    if value is None:
        raise AnsibleError(
            f"unit_name lookup: missing required variable '{name}' (is None)."
        )
    sval = str(value).strip()
    if not sval:
        raise AnsibleError(
            f"unit_name lookup: missing required variable '{name}' (empty)."
        )
    return sval.lower()


def _build_unit_name(
    systemctl_id: str, version: str, software_domain: str, suffix
) -> str:
    sid = _lower_required(systemctl_id, "systemctl_id")
    ver = _lower_required(version, "version")
    sw = _lower_required(software_domain, "SOFTWARE_DOMAIN")
    sfx = _normalize_suffix(suffix)

    # Keep template semantics compatible with your previous filter:
    # If id ends with "@", drop it and return "<base>.<ver>.<sw>@<suffix>" (e.g., "...@.service").
    if sid.endswith("@"):
        base = sid[:-1]
        return f"{base}.{ver}.{sw}@{sfx}"
    return f"{sid}.{ver}.{sw}{sfx}"


class LookupModule(LookupBase):
    """
    Lookup plugin entrypoint.

    Usage:
      - "{{ lookup('unit_name', system_service_id) }}"
      - "{{ lookup('unit_name', system_service_id, suffix='.timer') }}"
      - "{{ lookup('unit_name', system_service_id, suffix=False) }}"  # no suffix
    """

    def run(self, terms, variables=None, **kwargs):
        # Make variables accessible via templar
        self.set_options(var_options=variables, direct=kwargs)

        if not terms:
            raise AnsibleError(
                "unit_name lookup: at least one term (systemctl_id) is required."
            )

        # Read SOFTWARE_DOMAIN from current variable context
        available = getattr(self._templar, "available_variables", {}) or {}
        software_domain = available.get("SOFTWARE_DOMAIN")
        if not software_domain:
            raise AnsibleError(
                "unit_name lookup: SOFTWARE_DOMAIN is not defined in the variable context."
            )

        # Resolve version using the existing lookup('version')
        # We intentionally evaluate it through templating so it uses Ansible's lookup mechanism.
        version = self._templar.template("{{ lookup('version') }}")
        if not version or not str(version).strip():
            raise AnsibleError(
                "unit_name lookup: lookup('version') returned an empty value."
            )

        suffix = kwargs.get("suffix", None)

        results = []
        for term in terms:
            results.append(_build_unit_name(term, version, software_domain, suffix))

        return results
