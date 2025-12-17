from __future__ import annotations

from module_utils.config_utils import (
    get_app_conf,
    AppConfigKeyError,
    ConfigEntryNotSetError,
)  # noqa: F401
from module_utils.entity_name_utils import get_entity_name

from ansible.errors import AnsibleFilterError


def resource_filter(
    applications: dict,
    application_id: str,
    key: str,
    service_name: str,
    hard_default,
):
    """
    Lookup order:
      1) docker.services.<service_name or get_entity_name(application_id)>.<key>
      2) hard_default (mandatory)

    - service_name may be "" → will resolve to get_entity_name(application_id).
    - hard_default is mandatory (no implicit None).
    - required=False always.
    """
    try:
        primary_service = (
            service_name if service_name != "" else get_entity_name(application_id)
        )
        return get_app_conf(
            applications,
            application_id,
            f"docker.services.{primary_service}.{key}",
            False,
            hard_default,
        )
    except (AppConfigKeyError, ConfigEntryNotSetError) as e:
        raise AnsibleFilterError(str(e))


class FilterModule(object):
    def filters(self):
        return {
            "resource_filter": resource_filter,
        }
