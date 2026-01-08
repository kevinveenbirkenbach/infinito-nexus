#!/usr/bin/env python3
"""
Resolve galaxy_info.run_after transitively for a given role.

Usage:
  python -m cli.meta.applications.run_after_resolution <role_name>

Output:
  All resolved run_after role names separated by whitespaces (one line).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Set

import yaml


class RunAfterResolutionError(RuntimeError):
    """Raised when run_after resolution fails (e.g., cycle detected)."""


def repo_root_from_here() -> Path:
    # .../cli/meta/applications/run_after_resolution/__main__.py -> repo root is 5 parents up
    return Path(__file__).resolve().parents[4]


def roles_dir() -> Path:
    return repo_root_from_here() / "roles"


def role_meta_path(role_name: str) -> Path:
    return roles_dir() / role_name / "meta" / "main.yml"


def load_run_after(role_name: str) -> List[str]:
    """
    Read galaxy_info.run_after from roles/<role_name>/meta/main.yml.
    Returns a list of role names (strings). Missing meta/main.yml => [].
    """
    meta = role_meta_path(role_name)
    if not meta.exists():
        return []

    try:
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise RunAfterResolutionError(f"Failed to parse {meta}: {exc}") from exc

    galaxy_info = data.get("galaxy_info", {}) or {}
    run_after = galaxy_info.get("run_after", []) or []

    if run_after is None:
        return []
    if not isinstance(run_after, list):
        raise RunAfterResolutionError(
            f"Invalid run_after type in {meta}: expected list, got {type(run_after).__name__}"
        )

    cleaned: List[str] = []
    for item in run_after:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
        else:
            raise RunAfterResolutionError(
                f"Invalid run_after entry in {meta}: {item!r} (expected non-empty string)"
            )
    return cleaned


def resolve_run_after_transitively(start_role: str) -> List[str]:
    """
    Resolve run_after dependencies recursively (run_after of run_after, ...).

    - Detects cycles and raises RunAfterResolutionError on infinite loops.
    - Returns a topologically ordered list (prerequisites first).
    - The start_role itself is NOT included in the result.
    """
    rdir = roles_dir()
    if not (rdir / start_role).is_dir():
        raise RunAfterResolutionError(
            f"Unknown role: {start_role!r} (missing folder {rdir / start_role})"
        )

    # Cache run_after lists per role for speed and consistent error reporting
    cache: Dict[str, List[str]] = {}

    def ra(role: str) -> List[str]:
        if role not in cache:
            # Validate role existence when it is referenced
            if not (rdir / role).is_dir():
                raise RunAfterResolutionError(
                    f"Invalid run_after reference: {role!r} (missing folder {rdir / role})"
                )
            cache[role] = load_run_after(role)
        return cache[role]

    visited: Set[str] = set()
    stack: List[str] = []
    out: List[str] = []

    def dfs(node: str) -> None:
        if node in stack:
            # Cycle: show a readable path: A -> B -> C -> A
            idx = stack.index(node)
            cycle = stack[idx:] + [node]
            raise RunAfterResolutionError(
                f"Circular run_after dependency detected: {' -> '.join(cycle)}"
            )

        if node in visited:
            return

        visited.add(node)
        stack.append(node)

        for dep in ra(node):
            dfs(dep)

        stack.pop()

        # Post-order append yields a valid prerequisites-first ordering.
        if node != start_role:
            out.append(node)

    dfs(start_role)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve all galaxy_info.run_after dependencies of a role transitively."
    )
    parser.add_argument(
        "role_name", help="Name of the role folder under ./roles (e.g., web-app-taiga)"
    )
    args = parser.parse_args()

    resolved = resolve_run_after_transitively(args.role_name)
    print(" ".join(resolved))


if __name__ == "__main__":
    main()
