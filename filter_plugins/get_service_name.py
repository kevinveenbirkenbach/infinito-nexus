"""
Custom Ansible filter to build a systemctl unit name (always lowercase).

Rules:
- If `systemctl_id` ends with '@': drop the '@' and return
  "{systemctl_id_without_at}.{software_name}@{suffix_handling}".
- Else: return "{systemctl_id}.{software_name}{suffix_handling}".

Suffix handling:
- Default "" → automatically pick:
    - ".service" if no '@' in systemctl_id
    - ".timer"  if '@' in systemctl_id
- Explicit False → no suffix at all
- Any string → ".{suffix}" (lowercased)
"""

def get_service_name(systemctl_id, software_name, suffix=""):
    sid = str(systemctl_id).strip().lower()
    sw  = str(software_name).strip().lower()

    # Determine suffix
    if suffix is False:
        sfx = ""  # no suffix at all
    elif suffix == "" or suffix is None:
        sfx = ".timer" if sid.endswith("@") else ".service"
    else:
        sfx = "." + str(suffix).strip().lower()

    if sid.endswith("@"):
        base = sid[:-1]  # drop the trailing '@'
        return f"{base}.{sw}@{sfx}"
    else:
        return f"{sid}.{sw}{sfx}"


class FilterModule(object):
    def filters(self):
        return {"get_service_name": get_service_name}
