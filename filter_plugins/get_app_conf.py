from module_utils.config_utils import (
    AppConfigKeyError,
    ConfigEntryNotSetError,
    get_app_conf as _get_app_conf,
)

__all__ = [
    "get_app_conf",
    "AppConfigKeyError",
    "ConfigEntryNotSetError",
]


def get_app_conf(
    applications,
    application_id,
    config_path,
    strict=True,
    default=None,
    skip_missing_app=False,
):
    return _get_app_conf(
        applications=applications,
        application_id=application_id,
        config_path=config_path,
        strict=strict,
        default=default,
        skip_missing_app=skip_missing_app,
    )


class FilterModule:
    def filters(self):
        return {"get_app_conf": get_app_conf}
