from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        application_id = terms[0]
        base_gid = kwargs.get("base_gid", 10000)
        roles_dir = kwargs.get("roles_dir", "roles")

        if not os.path.isdir(roles_dir):
            raise AnsibleError(f"Roles directory '{roles_dir}' not found")

        sorted_ids = sorted(
            os.path.basename(os.path.dirname(os.path.dirname(path)))
            for path in (
                os.path.join(root, file_name)
                for root, _dirs, files in os.walk(roles_dir)
                for file_name in files
                if file_name == "main.yml" and os.path.basename(root) == "config"
            )
        )

        try:
            index = sorted_ids.index(application_id)
        except ValueError:
            raise AnsibleError(
                f"Application ID '{application_id}' not found in any role"
            )

        return [base_gid + index]
