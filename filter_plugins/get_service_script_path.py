# filter_plugins/get_service_script_path.py
# Custom Ansible filter to generate service script paths.

def get_service_script_path(system_service_id, script_type):
    """
    Build the path to a service script based on system_service_id and type.

    :param system_service_id: The identifier of the system service.
    :param script_type: The script type/extension (e.g., sh, py, yml).
    :return: The full path string.
    """
    if not system_service_id or not script_type:
        raise ValueError("Both system_service_id and script_type are required")

    return f"/opt/scripts/{system_service_id}/script.{script_type}"


class FilterModule(object):
    """ Custom filters for Ansible """

    def filters(self):
        return {
            "get_service_script_path": get_service_script_path
        }
