# lookup_plugins/compose_ca_inject_cmd.py
#
# Build the command to generate docker-compose.ca.override.yml via compose_ca_inject.py
#
# HARD FAIL PRINCIPLE:
# - No silent defaults.
# - kwargs.project is required (compose project name).
#
# It will call compose_ca_inject.py with docker compose config using:
# - base docker-compose.yml
# - docker-compose.override.yml
# (CA override is intentionally NOT included because it may not exist yet.)

from __future__ import annotations

import os
from typing import Any, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


def _as_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _require(d: Any, key: str, expected_type: Any, *, label: str) -> Any:
    if not isinstance(d, dict):
        raise AnsibleError(
            f"compose_ca_inject_cmd: {label} must be a dict, got {type(d)}"
        )
    if key not in d:
        raise AnsibleError(f"compose_ca_inject_cmd: missing required {label} '{key}'")
    val = d[key]
    if not isinstance(val, expected_type):
        raise AnsibleError(
            f"compose_ca_inject_cmd: {label} '{key}' must be {expected_type}, got {type(val)}"
        )
    return val


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        docker_compose = _require(variables, "docker_compose", dict, label="variable")
        dirs = docker_compose.get("directories")
        files = docker_compose.get("files")
        if not isinstance(dirs, dict) or not isinstance(files, dict):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.directories/files must be dicts"
            )

        instance_dir = _as_str(dirs.get("instance"))
        env_file = _as_str(files.get("env"))
        out_file = _as_str(files.get("docker_compose_ca_override"))
        base = _as_str(files.get("docker_compose"))
        override = _as_str(files.get("docker_compose_override"))

        if not instance_dir:
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.directories.instance is required"
            )
        if not out_file:
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose_ca_override is required"
            )
        if not base:
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose is required"
            )
        if not override:
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose_override is required"
            )

        ca_trust = _require(variables, "CA_TRUST", dict, label="variable")
        script_path = _as_str(
            _require(ca_trust, "inject_script", str, label="CA_TRUST")
        )
        ca_host = _as_str(_require(ca_trust, "cert_host", str, label="CA_TRUST"))
        wrapper_host = _as_str(
            _require(ca_trust, "wrapper_host", str, label="CA_TRUST")
        )

        project = _as_str(_require(kwargs, "project", str, label="kwargs"))
        if not project:
            raise AnsibleError(
                "compose_ca_inject_cmd: kwargs.project must be non-empty"
            )

        out_basename = os.path.basename(out_file)
        if not out_basename:
            raise AnsibleError(
                "compose_ca_inject_cmd: output basename resolved to empty"
            )

        # IMPORTANT: only base + override (no CA file here)
        compose_files = f"-f {base} -f {override}"

        cmd = [
            "python3",
            _shell_quote(script_path),
            "--chdir",
            _shell_quote(instance_dir),
            "--project",
            _shell_quote(project),
            "--compose-files",
            _shell_quote(compose_files),
        ]

        if env_file:
            cmd += ["--env-file", _shell_quote(env_file)]

        cmd += [
            "--out",
            _shell_quote(out_basename),
            "--ca-host",
            _shell_quote(ca_host),
            "--wrapper-host",
            _shell_quote(wrapper_host),
        ]

        return [" ".join(cmd)]
