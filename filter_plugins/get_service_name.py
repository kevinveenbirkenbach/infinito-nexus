# filter_plugins/get_service_name.py
"""
Custom Ansible filter to build a systemctl unit name (always lowercase).

Rules:
- If `systemctl_id` ends with '@': drop the '@' and return
  "{systemctl_id_without_at}.{software_name}@.{suffix}".
- Else: return "{systemctl_id}{software_name}.{suffix}".
"""

def get_service_name(systemctl_id, software_name, suffix="service"):
    sid = str(systemctl_id).strip().lower()
    sw  = str(software_name).strip().lower()
    sfx = str(suffix).strip().lower()

    if sid.endswith('@'):
        base = sid[:-1]  # drop the trailing '@'
        return f"{base}.{sw}@.{sfx}"
    else:
        return f"{sid}{sw}.{sfx}"


class FilterModule(object):
    def filters(self):
        return {"get_service_name": get_service_name}
