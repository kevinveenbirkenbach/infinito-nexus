from __future__ import annotations

from typing import TYPE_CHECKING

from utils.cache.yaml import load_yaml as _cached_load_yaml

from .errors import ServicesResolutionError

if TYPE_CHECKING:
    from pathlib import Path


def load_yaml_file(path: Path) -> dict:
    """Cached YAML load with the services-resolution error wrapper.
    Missing files / parse errors surface as `ServicesResolutionError`
    to keep the resolver's diagnostics consistent."""
    try:
        return _cached_load_yaml(path)
    except Exception as exc:
        raise ServicesResolutionError(f"Failed to parse {path}: {exc}") from exc
