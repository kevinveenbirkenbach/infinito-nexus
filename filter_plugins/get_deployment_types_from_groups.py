from __future__ import annotations

from module_utils.invokable import types_from_group_names


def get_deployment_types_from_groups(group_names):
    # Optional: add your own aliasing conventions here
    aliases = {
        "servers": "server",
        "workstations": "workstation",
    }
    return types_from_group_names(group_names or [], aliases=aliases)


class FilterModule(object):
    def filters(self):
        return {"get_deployment_types_from_groups": get_deployment_types_from_groups}
