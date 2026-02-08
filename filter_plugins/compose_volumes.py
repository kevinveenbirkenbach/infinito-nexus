from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

import yaml
from ansible.errors import AnsibleFilterError

from filter_plugins.docker_service_enabled import (
    FilterModule as _DockerServiceEnabledFilter,
)
from filter_plugins.get_app_conf import get_app_conf
from filter_plugins.get_entity_name import get_entity_name


def _to_plain(obj: Any) -> Any:
    """
    Convert Ansible/Jinja proxy types (e.g., AnsibleUnsafeText, AnsibleMapping)
    into plain Python types that PyYAML can always serialize.

    This does NOT change logic, only serialization stability.
    """

    if obj is None:
        return None

    # IMPORTANT:
    # Always cast string-like objects to real built-in `str`.
    # This avoids PyYAML "cannot represent an object" for Ansible proxy types.
    if isinstance(obj, str):
        return str(obj)

    # Scalars
    if isinstance(obj, (int, float, bool)):
        return obj

    # Mapping-like (including AnsibleMapping)
    if isinstance(obj, Mapping):
        return {str(_to_plain(k)): _to_plain(v) for k, v in obj.items()}

    # Sequence-like (but not string/bytes)
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        return [_to_plain(x) for x in obj]

    # Fallback: stringify unknown objects
    return str(obj)


def compose_volumes(
    applications: Dict[str, Any],
    application_id: str,
    *,
    database_volume: Optional[str] = None,
    extra_volumes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """
    Builds the top-level `volumes:` section for compose.

    Logic is identical to roles/sys-svc-compose/templates/volumes.yml.j2:

      - database volume if:
          is_docker_service_enabled(database)
          and not compose.services.database.shared

        name: database_volume   (no fallback!)

      - redis volume if:
          is_docker_service_enabled(redis)
          or compose.services.oauth2.enabled

        name: {{ application_id | get_entity_name }}_redis

    Manual volumes can be appended via extra_volumes (like adding YAML lines after an include).
    """

    # ------------------------------------------------------------------
    # Input validation (strict – filter must only work with valid input)
    # ------------------------------------------------------------------
    if applications is None:
        raise AnsibleFilterError("compose_volumes: 'applications' must not be None")
    if not isinstance(applications, dict):
        raise AnsibleFilterError("compose_volumes: 'applications' must be a dict")
    if not application_id or not isinstance(application_id, str):
        raise AnsibleFilterError(
            "compose_volumes: 'application_id' must be a non-empty string"
        )
    if application_id not in applications:
        raise AnsibleFilterError(
            f"compose_volumes: unknown application_id '{application_id}'"
        )

    volumes: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Database volume (same condition as Jinja2)
    # ------------------------------------------------------------------
    database_needed = _DockerServiceEnabledFilter.is_docker_service_enabled(
        applications, application_id, "database"
    ) and not bool(
        get_app_conf(
            applications=applications,
            application_id=application_id,
            config_path="compose.services.database.shared",
            strict=False,
            default=False,
            skip_missing_app=True,
        )
    )

    if database_needed:
        # Jinja2 behavior: name is exactly database_volume — no fallback
        if database_volume is None or str(database_volume).strip() == "":
            raise AnsibleFilterError(
                "compose_volumes: 'database_volume' must be set for application_id "
                f"'{application_id}' when database service is enabled and not shared"
            )
        volumes["database"] = {"name": database_volume}

    # ------------------------------------------------------------------
    # Redis volume (same condition as Jinja2)
    # ------------------------------------------------------------------
    if _DockerServiceEnabledFilter.is_docker_service_enabled(
        applications, application_id, "redis"
    ) or bool(
        get_app_conf(
            applications=applications,
            application_id=application_id,
            config_path="compose.services.oauth2.enabled",
            strict=False,
            default=False,
            skip_missing_app=True,
        )
    ):
        volumes["redis"] = {"name": f"{get_entity_name(application_id)}_redis"}

    # ------------------------------------------------------------------
    # Merge manual volumes (exactly like appending YAML after include)
    # ------------------------------------------------------------------
    if extra_volumes:
        volumes.update(extra_volumes)

    payload = {"volumes": _to_plain(volumes)}

    return yaml.safe_dump(
        payload,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()


class FilterModule(object):
    def filters(self):
        return {"compose_volumes": compose_volumes}
