from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Any
import yaml
import sys

from humanfriendly import parse_size

from module_utils.entity_name_utils import get_entity_name


def _deep_get(dct: dict, path: list[str]) -> Any:
    cur: Any = dct
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _load_yaml_file(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _gha_warning(message: str, *, title: str = "Validation") -> None:
    """
    Emit a GitHub Actions warning annotation.
    Safe outside GitHub Actions; it will just print the annotation line.
    """
    print(f"::warning title={title}::{message}", file=sys.stderr)


def _parse_storage_to_gb(value: Any) -> float:
    """
    Parse human-readable storage value to GB using humanfriendly.

    Examples:
      80G, 500GB, 1Ti, 1024MiB, 2 TB
    """
    if isinstance(value, (int, float)):
        return float(value)

    size_bytes = parse_size(str(value))
    return size_bytes / (1000**3)


def filter_roles_by_min_storage(
    *,
    role_names: Iterable[str],
    required_storage: str | int | float,
    emit_warnings: bool = False,
    roles_root: str | Path = "roles",
) -> List[str]:
    """
    Returns only those role_names whose roles/<role>/config/main.yml contains:
        services.docker.<entity_name>.min_storage >= required_storage

    If emit_warnings=True:
      - Missing config file, missing key, or invalid values will produce
        GitHub Actions warnings.

    Storage values are parsed using humanfriendly (80G, 1Ti, 500MB, etc.).
    """
    roles_root_path = Path(roles_root)
    out: List[str] = []

    try:
        required_gb = _parse_storage_to_gb(required_storage)
    except Exception as exc:
        raise ValueError(
            f"Invalid required_storage value: {required_storage!r}"
        ) from exc

    for role_name in role_names:
        role_dir = (roles_root_path / role_name).resolve()
        if not role_dir.is_dir():
            if emit_warnings:
                _gha_warning(
                    f"Role directory not found: {role_dir}",
                    title="min_storage validation",
                )
            continue


        entity_name = get_entity_name(role_name)
        if not entity_name:
            if emit_warnings:
                _gha_warning(
                    f"Could not derive entity_name from role_name '{role_name}'.",
                    title="min_storage validation",
                )
            continue

        cfg_path = role_dir / "config" / "main.yml"
        if not cfg_path.is_file():
            if emit_warnings:
                _gha_warning(
                    f"Missing config file: {cfg_path}",
                    title="min_storage validation",
                )
            continue

        try:
            cfg = _load_yaml_file(cfg_path)
        except Exception as exc:
            if emit_warnings:
                _gha_warning(
                    f"Failed to parse YAML: {cfg_path} ({exc})",
                    title="min_storage validation",
                )
            continue

        key_path = ["docker", "services", entity_name, "min_storage"]
        min_storage_val = _deep_get(cfg, key_path)

        if min_storage_val is None:
            if emit_warnings:
                _gha_warning(
                    f"Missing key docker.services.{entity_name}.min_storage in {cfg_path} (treating as 0GB)",
                    title="min_storage validation",
                )
            out.append(role_name)
            continue

        try:
            min_storage_gb = _parse_storage_to_gb(min_storage_val)
        except Exception as exc:
            if emit_warnings:
                _gha_warning(
                    f"Invalid min_storage value in {cfg_path}: {min_storage_val!r} ({exc})",
                    title="min_storage validation",
                )
            continue

        if min_storage_gb <= required_gb:
            out.append(role_name)
        else:
            if emit_warnings:
                _gha_warning(
                    f"{role_name} requires {min_storage_gb:.1f}GB but runner provides only {required_gb:.1f}GB",
                    title="min_storage validation",
                )

    return out
