from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import yaml

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        application_id = terms[0]
        base_gid = kwargs.get('base_gid', 10000)
        roles_dir = kwargs.get('roles_dir', 'roles')

        if not os.path.isdir(roles_dir):
            raise AnsibleError(f"Roles directory '{roles_dir}' not found")

        matched_roles = []

        for root, dirs, files in os.walk(roles_dir):
            if os.path.basename(root) == "vars" and "main.yml" in files:
                vars_path = os.path.join(root, "main.yml")
                try:
                    with open(vars_path, 'r') as f:
                        data = yaml.safe_load(f) or {}
                        app_id = data.get('application_id')
                        if app_id:
                            matched_roles.append((app_id, vars_path))
                except Exception as e:
                    raise AnsibleError(f"Error parsing {vars_path}: {e}")

        # sort alphabetically by application_id
        sorted_ids = sorted(app_id for app_id, _ in matched_roles)

        try:
            index = sorted_ids.index(application_id)
        except ValueError:
            raise AnsibleError(f"Application ID '{application_id}' not found in any role")

        return [base_gid + index]
