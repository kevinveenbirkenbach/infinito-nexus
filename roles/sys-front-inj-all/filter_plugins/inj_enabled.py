import sys
import os
from module_utils.config_utils import get_app_conf

# allow imports from module_utils (same trick as your get_app_conf filter)
base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
mu = os.path.join(base, "module_utils")
for p in (base, mu):
    if p not in sys.path:
        sys.path.insert(0, p)


def inj_enabled_filter(
    applications, application_id, features, prefix="features", default=False
):
    """
    Build a dict {feature: value} by reading the feature flags under the given prefix for the selected application.
    Uses get_app_conf with strict=False so missing keys just return the default.
    """
    result = {}
    for f in features:
        path = f"{prefix}.{f}" if prefix else f
        result[f] = get_app_conf(
            applications, application_id, path, strict=False, default=default
        )
    return result


class FilterModule(object):
    def filters(self):
        return {
            "inj_enabled": inj_enabled_filter,
        }
