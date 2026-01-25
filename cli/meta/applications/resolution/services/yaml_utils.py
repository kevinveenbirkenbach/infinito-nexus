from __future__ import annotations

from pathlib import Path

import yaml

from .errors import ServicesResolutionError


def load_yaml_file(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ServicesResolutionError(f"Failed to parse {path}: {exc}") from exc
