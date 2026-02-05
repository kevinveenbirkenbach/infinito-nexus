from __future__ import annotations

import os
from typing import Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.docker_paths_utils import get_docker_paths


def _as_str(v) -> str:
    return "" if v is None else str(v).strip()


def _get_instances_base(variables: Optional[dict]) -> str:
    # 1) Prefer Ansible vars
    if variables and "PATH_DOCKER_COMPOSE_INSTANCES" in variables:
        v = _as_str(variables.get("PATH_DOCKER_COMPOSE_INSTANCES"))
        if v:
            return v

    # 2) Fallback to environment
    env_v = _as_str(os.environ.get("PATH_DOCKER_COMPOSE_INSTANCES"))
    if env_v:
        return env_v

    raise AnsibleError(
        "lookup('docker', ...): PATH_DOCKER_COMPOSE_INSTANCES missing "
        "(neither Ansible var nor environment variable is set)"
    )


class LookupModule(LookupBase):
    """
    Usage:
      - {{ (lookup('docker', application_id, wantlist=True) | first) }}
      - {{ (lookup('docker', application_id, wantlist=True) | first).directories.instance }}
      - {{ (lookup('docker', application_id, wantlist=True) | first).files.docker_compose }}

    Optional explicit base path:
      - {{ lookup('docker', application_id, '/opt/docker/') }}
    """

    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        if not terms or len(terms) not in (1, 2):
            raise AnsibleError(
                "lookup('docker', ...): usage lookup('docker', application_id [, path_instances])"
            )

        application_id = _as_str(terms[0])
        if not application_id:
            raise AnsibleError("lookup('docker', ...): application_id is empty")

        path_instances = _as_str(terms[1]) if len(terms) == 2 else _get_instances_base(variables)
        if not path_instances:
            raise AnsibleError("lookup('docker', ...): instances base path resolved to empty")

        return [get_docker_paths(application_id, path_instances)]
