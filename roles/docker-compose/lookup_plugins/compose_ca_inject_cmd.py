# roles/docker-compose/lookup_plugins/compose_ca_inject_cmd.py
from __future__ import annotations

import os
from typing import Any, Optional

import yaml
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.plugins.loader import lookup_loader

from module_utils.entity_name_utils import get_entity_name
from module_utils.templating import render_ansible_strict


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

        if not terms or len(terms) != 1:
            raise AnsibleError(
                "compose_ca_inject_cmd: exactly one term required (application_id)"
            )

        application_id = _as_str(terms[0])
        if not application_id:
            raise AnsibleError("compose_ca_inject_cmd: application_id is empty")

        project = _as_str(get_entity_name(application_id))
        if not project:
            raise AnsibleError("compose_ca_inject_cmd: resolved project is empty")

        raw_dc = variables.get("docker_compose", None)
        if raw_dc is None:
            raise AnsibleError(
                "compose_ca_inject_cmd: missing required variable 'docker_compose'"
            )

        templar = getattr(self, "_templar", None)
        rendered_dc = _maybe_template(templar, raw_dc)
        docker_compose = _coerce_to_dict(rendered_dc, "variable docker_compose")

        dirs = docker_compose.get("directories")
        files = docker_compose.get("files")
        if not isinstance(dirs, dict) or not isinstance(files, dict):
            raise AnsibleError(
                "compose_ca_inject_cmd: docker_compose.directories/files must be dicts"
            )

        instance_dir = render_ansible_strict(
            templar=templar,
            raw=dirs.get("instance"),
            var_name="docker_compose.directories.instance",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        env_file = render_ansible_strict(
            templar=templar,
            raw=files.get("env"),
            var_name="docker_compose.files.env",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        out_file = render_ansible_strict(
            templar=templar,
            raw=files.get("docker_compose_ca_override"),
            var_name="docker_compose.files.docker_compose_ca_override",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )

        ca_trust = _require(variables, "CA_TRUST", dict, label="variable")

        script_path = render_ansible_strict(
            templar=templar,
            raw=_require(ca_trust, "inject_script", str, label="CA_TRUST"),
            var_name="CA_TRUST.inject_script",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        ca_host = render_ansible_strict(
            templar=templar,
            raw=_require(ca_trust, "cert_host", str, label="CA_TRUST"),
            var_name="CA_TRUST.cert_host",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        wrapper_host = render_ansible_strict(
            templar=templar,
            raw=_require(ca_trust, "wrapper_host", str, label="CA_TRUST"),
            var_name="CA_TRUST.wrapper_host",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        trust_name = render_ansible_strict(
            templar=templar,
            raw=_require(ca_trust, "trust_name", str, label="CA_TRUST"),
            var_name="CA_TRUST.trust_name",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )

        out_basename = os.path.basename(out_file)
        if not out_basename:
            raise AnsibleError(
                "compose_ca_inject_cmd: output basename resolved to empty"
            )

        compose_f_args_lkp = lookup_loader.get(
            "compose_f_args", self._loader, self._templar
        )
        compose_files = compose_f_args_lkp.run(
            [application_id], variables=variables, include_ca=False
        )[0]
        if not _as_str(compose_files):
            raise AnsibleError("compose_ca_inject_cmd: compose_f_args returned empty")

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
            "--trust-name",
            _shell_quote(trust_name),
        ]

        return [" ".join(cmd)]
