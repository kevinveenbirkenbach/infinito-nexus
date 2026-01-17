from __future__ import annotations

from typing import Any, Dict, Optional

import yaml
from ansible.errors import AnsibleFilterError

from filter_plugins.docker_service_enabled import (
    FilterModule as _DockerServiceEnabledFilter,
)
from filter_plugins.get_app_conf import get_app_conf
from filter_plugins.get_entity_name import get_entity_name


def compose_volumes(
    applications: Dict[str, Any],
    application_id: str,
    *,
    database_volume: Optional[str] = None,
    extra_volumes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """
    Builds the top-level `volumes:` section for docker-compose.

    Logic is identical to roles/docker-compose/templates/volumes.yml.j2:

      - database volume if:
          is_docker_service_enabled(database)
          and not docker.services.database.shared

        name: database_volume   (no fallback!)

      - redis volume if:
          is_docker_service_enabled(redis)
          or docker.services.oauth2.enabled

        name: {{ application_id | get_entity_name }}_redis
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
            config_path="docker.services.database.shared",
            strict=False,
            default=False,
            skip_missing_app=True,
        )
    )

    if database_needed:
        # Jinja2 behavior: name is exactly database_volume — no fallback
        if database_volume is None or str(database_volume).strip() == "":
            raise AnsibleFilterError(
                f"compose_volumes: 'database_volume' must be set for application_id "
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
            config_path="docker.services.oauth2.enabled",
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

    return yaml.safe_dump(
        {"volumes": volumes},
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()


class FilterModule(object):
    def filters(self):
        return {"compose_volumes": compose_volumes}
