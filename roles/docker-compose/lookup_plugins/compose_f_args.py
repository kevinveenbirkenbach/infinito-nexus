# lookup_plugins/compose_f_args.py
#
# Build docker compose "-f <file>" arguments for an application instance.
#
# HARD FAIL PRINCIPLE:
# - No defaults that change behavior.
# - Fail loudly if required variables or tls_resolve output is missing/invalid.
#
# Rules:
# - Always include base docker-compose.yml
# - Always include docker-compose.override.yml
# - Include docker-compose.ca.override.yml ONLY when:
#     TLS is enabled AND TLS mode == "self_signed"
#
# Requires:
# - docker_compose.files.docker_compose
# - docker_compose.files.docker_compose_override
# - docker_compose.files.docker_compose_ca_override (required when enabled+self_signed)
# - tls_resolve lookup plugin available

from __future__ import annotations

from typing import Any, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.plugins.loader import lookup_loader


def _as_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _require_dict(d: Any, label: str) -> dict:
    if not isinstance(d, dict):
        raise AnsibleError(f"compose_f_args: {label} must be a dict, got {type(d)}")
    return d


def _require_key(d: dict, key: str, expected_type: Any, *, label: str) -> Any:
    if key not in d:
        raise AnsibleError(f"compose_f_args: missing required {label} '{key}'")
    val = d[key]
    if not isinstance(val, expected_type):
        raise AnsibleError(
            f"compose_f_args: {label} '{key}' must be {expected_type}, got {type(val)}"
        )
    return val


class LookupModule(LookupBase):
    def run(self, terms, variables: Optional[dict] = None, **kwargs):
        variables = variables or {}

        if not terms or len(terms) != 1:
            raise AnsibleError(
                "compose_f_args: exactly one term required (application_id)"
            )

        application_id = _as_str(terms[0])
        if not application_id:
            raise AnsibleError("compose_f_args: application_id is empty")

        docker_compose = _require_key(
            variables, "docker_compose", dict, label="variable"
        )
        docker_compose = _require_dict(docker_compose, "docker_compose")

        files = docker_compose.get("files")
        files = _require_dict(files, "docker_compose.files")

        base = _as_str(files.get("docker_compose"))
        override = _as_str(files.get("docker_compose_override"))
        ca_override = _as_str(files.get("docker_compose_ca_override"))

        if not base:
            raise AnsibleError(
                "compose_f_args: docker_compose.files.docker_compose is required"
            )
        if not override:
            raise AnsibleError(
                "compose_f_args: docker_compose.files.docker_compose_override is required"
            )

        # Resolve TLS using existing strict lookup.
        tls_resolver = lookup_loader.get("tls_resolve", self._loader, self._templar)
        tls = tls_resolver.run([application_id], variables=variables)[0]

        if not isinstance(tls, dict):
            raise AnsibleError(
                f"compose_f_args: tls_resolve returned non-dict: {type(tls)}"
            )

        if "enabled" not in tls:
            raise AnsibleError("compose_f_args: tls_resolve did not return 'enabled'")
        if "mode" not in tls:
            raise AnsibleError("compose_f_args: tls_resolve did not return 'mode'")

        enabled = bool(tls["enabled"])
        mode = _as_str(tls["mode"])
        if not mode:
            raise AnsibleError("compose_f_args: tls_resolve returned empty 'mode'")

        parts = [f"-f {base}", f"-f {override}"]

        if enabled and mode == "self_signed":
            if not ca_override:
                raise AnsibleError(
                    "compose_f_args: docker_compose.files.docker_compose_ca_override is required "
                    "when TLS is enabled and mode is self_signed"
                )
            parts.append(f"-f {ca_override}")

        return [" ".join(parts)]
