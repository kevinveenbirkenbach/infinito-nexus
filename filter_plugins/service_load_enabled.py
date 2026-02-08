from module_utils.config_utils import get_app_conf as _get_app_conf


def service_load_enabled(applications, application_id, service_name, default=False):
    """
    Return True if compose.services.<service_name>.enabled AND .shared are true.

    Uses the existing module_utils.config_utils.get_app_conf implementation,
    so schema/strict/default behavior stays consistent across the codebase.

    Usage:
      {{ applications | service_load_enabled(application_id, 'ldap') }}
    """

    # We explicitly use strict=False here to behave like a "safe boolean probe".
    enabled = _get_app_conf(
        applications=applications,
        application_id=application_id,
        config_path=f"compose.services.{service_name}.enabled",
        strict=False,
        default=default,
        skip_missing_app=False,
    )

    shared = _get_app_conf(
        applications=applications,
        application_id=application_id,
        config_path=f"compose.services.{service_name}.shared",
        strict=False,
        default=default,
        skip_missing_app=False,
    )

    return bool(enabled) and bool(shared)


class FilterModule:
    def filters(self):
        return {"service_load_enabled": service_load_enabled}
