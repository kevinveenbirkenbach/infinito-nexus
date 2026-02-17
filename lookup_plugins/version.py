# -*- coding: utf-8 -*-
"""
Ansible lookup plugin: version

No parameters.
Reads pyproject.toml relative to this plugin file:
<repo>/lookup_plugins/version.py -> <repo>/pyproject.toml

Resolution order:
1) [project].version (PEP 621)
2) [tool.poetry].version (Poetry fallback)
"""

from __future__ import annotations

import os
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    import tomllib  # Python 3.11+
except Exception:
    try:
        import tomli as tomllib  # type: ignore
    except Exception as exc:
        raise AnsibleError(
            "version lookup requires 'tomllib' (Python 3.11+) "
            "or the 'tomli' package installed on the control node."
        ) from exc


def _get_nested(data: dict, path: list[str]):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        # Intentionally ignore terms/kwargs — no parameters supported

        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        pyproject_path = os.path.normpath(
            os.path.join(plugin_dir, "..", "pyproject.toml")
        )

        if not os.path.exists(pyproject_path):
            raise AnsibleError(f"version lookup: file not found: {pyproject_path}")

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as exc:
            raise AnsibleError(
                f"version lookup: failed to parse TOML: {pyproject_path}: {exc}"
            ) from exc

        version = _get_nested(data, ["project", "version"])
        if not version:
            version = _get_nested(data, ["tool", "poetry", "version"])

        if not version or not isinstance(version, str) or not version.strip():
            raise AnsibleError(
                f"version lookup: could not extract version from {pyproject_path}. "
                "Tried [project].version and [tool.poetry].version."
            )

        return [version.strip()]
