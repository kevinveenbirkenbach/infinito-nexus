# lookup_plugins/docker.py
from __future__ import annotations

from typing import Any, Dict, Optional
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from filter_plugins.get_docker_paths import get_docker_paths  # as in your repo


def _as_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _deep_get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            raise AnsibleError(f"lookup('docker'): invalid path '{path}'")
        cur = cur[key]
    return cur


class LookupModule(LookupBase):
    """
    lookup('docker', application_id[, dotted.path])
    """

    def run(self, terms, variables: Optional[Dict[str, Any]] = None, **kwargs):
        if not terms or len(terms) > 2:
            raise AnsibleError("lookup('docker', application_id[, dotted.path])")

        application_id = _as_str(terms[0])
        if not application_id:
            raise AnsibleError("lookup('docker'): application_id is empty")

        base = _as_str((variables or {}).get("PATH_DOCKER_COMPOSE_INSTANCES"))
        if not base:
            raise AnsibleError(
                "lookup('docker'): PATH_DOCKER_COMPOSE_INSTANCES not set"
            )

        docker_dict = get_docker_paths(application_id, base)

        if len(terms) == 2:
            path = _as_str(terms[1])
            if "." not in path:
                raise AnsibleError("lookup('docker'): only dotted paths are allowed")
            return [_deep_get(docker_dict, path)]

        return [docker_dict]
