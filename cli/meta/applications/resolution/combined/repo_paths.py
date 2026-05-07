from __future__ import annotations

from pathlib import Path
from . import PROJECT_ROOT


def roles_dir() -> Path:
    return PROJECT_ROOT / "roles"


def role_dir(role_name: str) -> Path:
    return roles_dir() / role_name


def role_meta_path(role_name: str) -> Path:
    return role_dir(role_name) / "meta" / "main.yml"


def role_vars_path(role_name: str) -> Path:
    return role_dir(role_name) / "vars" / "main.yml"


def role_services_path(role_name: str) -> Path:
    """Return the post-req-008 services manifest path."""
    return role_dir(role_name) / "meta" / "services.yml"


def role_config_path(role_name: str) -> Path:
    """Backwards-compatible alias that now points at meta/services.yml.

    Kept so call sites that historically asked for "config" still work; the
    contents are the services map directly (no `compose.services` wrapper).
    """
    return role_services_path(role_name)
