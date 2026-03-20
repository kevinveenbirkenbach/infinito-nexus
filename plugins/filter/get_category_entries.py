# Custom Ansible filter to get all role names under "roles/" with a given prefix.

import os


def get_category_entries(prefix, roles_path="roles"):
    """
    Returns a list of role names under the given roles_path
    that start with the specified prefix.

    :param prefix: String prefix to match role names.
    :param roles_path: Path to the roles directory (default: 'roles').
    :return: List of matching role names.
    """
    if not os.path.isdir(roles_path):
        return []

    roles = []
    for entry in os.listdir(roles_path):
        full_path = os.path.join(roles_path, entry)
        if os.path.isdir(full_path) and entry.startswith(prefix):
            roles.append(entry)

    return sorted(roles)


class FilterModule(object):
    """Custom filters for Ansible"""

    def filters(self):
        return {"get_category_entries": get_category_entries}
