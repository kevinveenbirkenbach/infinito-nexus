# cli/meta/applications/resolution/combined/repo_paths.py
from __future__ import annotations

from pathlib import Path


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[5]


def roles_dir() -> Path:
    return repo_root_from_here() / "roles"


def role_dir(role_name: str) -> Path:
    return roles_dir() / role_name


def role_meta_path(role_name: str) -> Path:
    return role_dir(role_name) / "meta" / "main.yml"


def role_vars_path(role_name: str) -> Path:
    return role_dir(role_name) / "vars" / "main.yml"


def role_config_path(role_name: str) -> Path:
    return role_dir(role_name) / "config" / "main.yml"
