# lookup_plugins/domain.py
from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):
    """
    Usage:
      {{ lookup('domain', application_id) }}

    Reads:
      - variables['domains'] (required)
    Returns:
      - domain as string (resolved via utils.domains.primary_domain.get_domain)
    """

    def run(self, terms, variables: Optional[Dict[str, Any]] = None, **kwargs):
        if not terms or len(terms) != 1:
            raise AnsibleError(
                "lookup('domain', application_id) expects exactly 1 term"
            )

        application_id = terms[0]
        if not isinstance(application_id, str) or not application_id.strip():
            raise AnsibleError(
                f"lookup('domain'): application_id must be a non-empty string, got {application_id!r}"
            )

        variables = variables or {}
        if "domains" not in variables:
            raise AnsibleError("lookup('domain'): missing required variable 'domains'")

        # Make utils importable (project_root/utils)
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(plugin_dir, "..", ".."))
        if project_root not in sys.path:
            sys.path.append(project_root)

        try:
            from utils.domains.primary_domain import get_domain
        except Exception as e:
            raise AnsibleError(
                f"lookup('domain'): could not import utils.domains.primary_domain.get_domain: {e}"
            )

        try:
            domain = get_domain(variables["domains"], application_id.strip())
        except Exception as e:
            raise AnsibleError(
                f"lookup('domain'): failed to resolve domain for '{application_id}': {e}"
            )

        return [domain]
