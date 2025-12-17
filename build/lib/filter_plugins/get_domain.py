#!/usr/bin/python
import os
import sys
from ansible.errors import AnsibleFilterError

class FilterModule(object):
    def filters(self):
        plugin_dir      = os.path.dirname(__file__)
        project_root    = os.path.dirname(plugin_dir)
        module_utils    = os.path.join(project_root, 'module_utils')
        if module_utils not in sys.path:
            sys.path.append(module_utils)

        try:
            from domain_utils import get_domain
        except ImportError as e:
            raise AnsibleFilterError(f"could not import domain_utils: {e}")

        return {'get_domain': get_domain}
