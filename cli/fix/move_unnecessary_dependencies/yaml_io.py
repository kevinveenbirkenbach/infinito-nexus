"""YAML round-trip + role-discovery helpers shared across the fix package."""

from __future__ import annotations

import glob
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.scalarstring import SingleQuotedScalarString

    _HAVE_RUAMEL = True
except Exception:
    _HAVE_RUAMEL = False

if not _HAVE_RUAMEL:
    logger.error(
        "ruamel.yaml is required to preserve comments/quotes. "
        "Install with: pip install ruamel.yaml"
    )
    sys.exit(3)

yaml_rt = YAML()
yaml_rt.preserve_quotes = True
yaml_rt.width = 10**9


def backup(path: str) -> None:
    if Path(path).exists():
        shutil.copy2(path, path + ".bak")


def read_text(path: str) -> str:
    try:
        with Path(path).open(encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def load_yaml_rt(path: str):
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = yaml_rt.load(f)
        return data if data is not None else CommentedMap()
    except FileNotFoundError:
        return CommentedMap()
    except Exception as e:
        print(f"[WARN] Failed to parse YAML: {path}: {e}", file=sys.stderr)
        return CommentedMap()


def dump_yaml_rt(data, path: str) -> None:
    backup(path)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml_rt.dump(data, f)


def sq(value: str):
    """Single-quoted scalar for consistent ruamel quoting."""
    return SingleQuotedScalarString(value)


def roles_root(project_root: str) -> str:
    return str(Path(project_root) / "roles")


def iter_role_dirs(project_root: str) -> list[str]:
    return [
        d
        for d in glob.glob(str(Path(roles_root(project_root)) / "*"))
        if Path(d).is_dir()
    ]


def role_name_from_dir(role_dir: str) -> str:
    return Path(role_dir.rstrip(os.sep)).name


def path_if_exists(*parts: str) -> str | None:
    p = str(Path(*parts))
    return p if Path(p).exists() else None


def gather_yaml_files(base: str, patterns: list[str]) -> list[str]:
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(str(Path(base) / pat), recursive=True))
    return [f for f in files if Path(f).is_file()]
