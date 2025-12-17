from ansible.errors import AnsibleFilterError
import sys
import os


def get_url(domains, application_id, protocol):
    plugin_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(plugin_dir)
    module_utils = os.path.join(project_root, "module_utils")
    if module_utils not in sys.path:
        sys.path.append(module_utils)

    try:
        from domain_utils import get_domain
    except ImportError as e:
        raise AnsibleFilterError(f"could not import domain_utils: {e}")

    if not isinstance(protocol, str):
        raise AnsibleFilterError("Protocol must be a string")
    return f"{protocol}://{get_domain(domains, application_id)}"
