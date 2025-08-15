# roles/sys-srv-web-inj-compose/filter_plugins/inj_snippets.py
"""
Jinja filter: `inj_features(kind)` filters a list of features to only those
that actually provide the corresponding snippet template file.

- kind='head' -> roles/sys-srv-web-inj-<feature>/templates/head_sub.j2
- kind='body' -> roles/sys-srv-web-inj-<feature>/templates/body_sub.j2

If the feature's role directory (roles/sys-srv-web-inj-<feature>) does not
exist, this filter raises FileNotFoundError.

Usage in a template:
    {% set head_features = SRV_WEB_INJ_COMP_FEATURES_ALL | inj_features('head') %}
    {% set body_features = SRV_WEB_INJ_COMP_FEATURES_ALL | inj_features('body') %}
"""

import os

# This file lives at: roles/sys-srv-web-inj-compose/filter_plugins/inj_snippets.py
_THIS_DIR = os.path.dirname(__file__)
_ROLE_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))   # roles/sys-srv-web-inj-compose
_ROLES_DIR = os.path.abspath(os.path.join(_ROLE_DIR, ".."))  # roles

def _feature_role_dir(feature: str) -> str:
    return os.path.join(_ROLES_DIR, f"sys-srv-web-inj-{feature}")

def _has_snippet(feature: str, kind: str) -> bool:
    if kind not in ("head", "body"):
        raise ValueError("kind must be 'head' or 'body'")

    role_dir = _feature_role_dir(feature)
    if not os.path.isdir(role_dir):
        raise FileNotFoundError(
            f"[inj_snippets] Expected role directory not found for feature "
            f"'{feature}': {role_dir}"
        )

    path = os.path.join(role_dir, "templates", f"{kind}_sub.j2")
    return os.path.exists(path)

def inj_features_filter(features, kind: str = "head"):
    if not isinstance(features, (list, tuple)):
        return []
    # Validation + filtering in one pass; will raise if a role dir is missing.
    valid = []
    for f in features:
        name = str(f)
        if _has_snippet(name, kind):
            valid.append(name)
    return valid

class FilterModule(object):
    def filters(self):
        return {
            "inj_features": inj_features_filter,
        }
