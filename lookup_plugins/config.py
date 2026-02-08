# lookup_plugins/config.py
from __future__ import annotations

from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.config_utils import get_app_conf


class LookupModule(LookupBase):
    """
    lookup('config', application_id, config_path[, default])

    - applications is read from the Ansible variable `applications`
    - default behavior is strict=True (missing keys raise)
    - if a 3rd argument (default) is provided, strict=False and that default is returned
    - parameters:
        1) application_id
        2) config_path
        3) optional default value
    """

    def run(self, terms, variables: Optional[Dict[str, Any]] = None, **kwargs):
        if not terms or len(terms) not in (2, 3):
            raise AnsibleError(
                "lookup('config', application_id, config_path[, default]) expects 2 or 3 terms."
            )

        application_id = terms[0]
        config_path = terms[1]

        default_provided = len(terms) == 3
        default_value = terms[2] if default_provided else None
        strict = not default_provided

        if variables is None or "applications" not in variables:
            raise AnsibleError(
                "lookup('config', ...): required Ansible variable 'applications' is not defined."
            )

        applications = variables.get("applications")

        if not isinstance(applications, dict):
            raise AnsibleError(
                "lookup('config', ...): Ansible variable 'applications' must be a dict/mapping."
            )

        value = get_app_conf(
            applications=applications,
            application_id=application_id,
            config_path=config_path,
            strict=strict,
            default=default_value,
            skip_missing_app=False,
        )

        # lookup plugins must return a list
        return [value]
