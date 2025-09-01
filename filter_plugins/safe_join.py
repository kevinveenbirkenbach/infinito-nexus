"""
Ansible filter plugin that joins a base string and a tail path safely.
Raises ValueError if base or tail is None.
"""

def safe_join(base, tail):
    """
    Safely join base and tail into a path or URL.

    - base: the base string. Must not be None.
    - tail: the string to append. Must not be None.
    - On ValueError, caller should handle it.
    """
    if base is None or tail is None:
        raise ValueError("safe_join: base and tail must not be None")

    try:
        base_str = str(base).rstrip('/')
        tail_str = str(tail).lstrip('/')
        return f"{base_str}/{tail_str}"
    except Exception:
        return ''


class FilterModule(object):
    def filters(self):
        return {
            'safe_join': safe_join,
        }
