#!/usr/bin/env python3
import os
import sys
from ansible.errors import AnsibleFilterError


class FilterModule(object):
    def filters(self):
        plugin_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(plugin_dir, "..", ".."))
        if project_root not in sys.path:
            sys.path.append(project_root)

        try:
            from module_utils.domains.primary_domain import get_domain
        except ImportError as e:
            raise AnsibleFilterError(
                f"could not import module_utils.domains.primary_domain: {e}"
            )

        return {"get_domain": get_domain}
