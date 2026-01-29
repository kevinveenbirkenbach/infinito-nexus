# roles/docker-compose/lookup_plugins/compose_ca_inject_cmd.py
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

import yaml
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.jinja_strict import render_strict


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


def _coerce_to_dict(v: Any, label: str) -> dict:
    """
    Coerce a value into a dict:
      - accept dict directly
      - accept YAML/JSON encoded string and parse it
    """
    if isinstance(v, dict):
        return v

    if isinstance(v, str):
        s = v.strip()
        if not s:
            raise AnsibleError(f"compose_ca_inject_cmd: {label} is empty string")
        try:
            loaded = yaml.safe_load(s)
        except Exception as exc:
            raise AnsibleError(
                f"compose_ca_inject_cmd: {label} could not be parsed as YAML: {exc}"
            )
        if isinstance(loaded, dict):
            return loaded
        raise AnsibleError(
            f"compose_ca_inject_cmd: {label} parsed but is not a dict (got {type(loaded)})"
        )

    raise AnsibleError(f"compose_ca_inject_cmd: {label} must be a dict, got {type(v)}")


def _maybe_template(templar: Any, value: Any) -> Any:
    """
    Render via Ansible templar if available.
    Unit tests may not inject a templar -> then we skip templating.
    """
    if isinstance(value, (dict, list, tuple, int, float, bool)) or value is None:
        return value
    if templar is None:
        return value
    tpl = getattr(templar, "template", None)
    if callable(tpl):
        return tpl(value)
    return value


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        raw_dc = variables.get("docker_compose", None)
        if raw_dc is None:
            raise AnsibleError(
                "compose_ca_inject_cmd: missing required variable 'docker_compose'"
            )

        rendered_dc = _maybe_template(getattr(self, "_templar", None), raw_dc)
        docker_compose = _coerce_to_dict(rendered_dc, "variable docker_compose")

        dirs = docker_compose.get("directories")
        files = docker_compose.get("files")
        if not isinstance(dirs, dict) or not isinstance(files, dict):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.directories/files must be dicts"
            )

        instance_dir = render_strict(
            dirs.get("instance"),
            variables=variables,
            var_name="docker_compose.directories.instance",
            err_prefix="compose_ca_inject_cmd",
        )
        env_file = render_strict(
            files.get("env"),
            variables=variables,
            var_name="docker_compose.files.env",
            err_prefix="compose_ca_inject_cmd",
        )
        out_file = render_strict(
            files.get("docker_compose_ca_override"),
            variables=variables,
            var_name="docker_compose.files.docker_compose_ca_override",
            err_prefix="compose_ca_inject_cmd",
        )
        base = render_strict(
            files.get("docker_compose"),
            variables=variables,
            var_name="docker_compose.files.docker_compose",
            err_prefix="compose_ca_inject_cmd",
        )
        override = render_strict(
            files.get("docker_compose_override"),
            variables=variables,
            var_name="docker_compose.files.docker_compose_override",
            err_prefix="compose_ca_inject_cmd",
        )

        if not _as_str(instance_dir):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.directories.instance is required"
            )
        if not _as_str(out_file):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose_ca_override is required"
            )
        if not _as_str(base):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose is required"
            )
        if not _as_str(override):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.files.docker_compose_override is required"
            )

        ca_trust = _require(variables, "CA_TRUST", dict, label="variable")

        script_path = render_strict(
            _require(ca_trust, "inject_script", str, label="CA_TRUST"),
            variables=variables,
            var_name="CA_TRUST.inject_script",
            err_prefix="compose_ca_inject_cmd",
        )
        ca_host = render_strict(
            _require(ca_trust, "cert_host", str, label="CA_TRUST"),
            variables=variables,
            var_name="CA_TRUST.cert_host",
            err_prefix="compose_ca_inject_cmd",
        )
        wrapper_host = render_strict(
            _require(ca_trust, "wrapper_host", str, label="CA_TRUST"),
            variables=variables,
            var_name="CA_TRUST.wrapper_host",
            err_prefix="compose_ca_inject_cmd",
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

        if _as_str(env_file):
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
