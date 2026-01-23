#!/usr/bin/python
import os
import sys
from ansible.errors import AnsibleFilterError


class FilterModule(object):
    def filters(self):
        plugin_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(plugin_dir)
        module_utils = os.path.join(project_root, "module_utils")
        if module_utils not in sys.path:
            sys.path.append(module_utils)

        try:
            from domain_utils import get_domain
        except ImportError as e:
            raise AnsibleFilterError(f"could not import domain_utils: {e}")

        def has_domain(domains, application_id):
            """
            Return True if get_domain(domains, application_id) succeeds,
            False if it raises an AnsibleFilterError.
            """
            try:
                get_domain(domains, application_id)
                return True
            except AnsibleFilterError:
                return False

        return {
            "has_domain": has_domain,
        }
