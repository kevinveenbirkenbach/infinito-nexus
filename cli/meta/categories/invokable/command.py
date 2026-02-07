#!/usr/bin/env python3
"""
CLI for extracting invokable or non-invokable role paths from a nested roles YAML file.

Fixed-path resolution without marker scanning.

Layout assumption:
  <repo_root>/cli/meta/categories/invokable/command.py
  <repo_root>/filter_plugins/...
  <repo_root>/roles/categories.yml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def _project_root_from_here() -> Path:
    # command.py -> invokable(0) -> categories(1) -> meta(2) -> cli(3) -> repo_root(4)
    return Path(__file__).resolve().parents[4]


def _default_roles_file() -> str:
    repo_root = _project_root_from_here()
    return str(repo_root / "roles" / "categories.yml")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract invokable or non-invokable role paths from a nested roles YAML file."
    )
    parser.add_argument(
        "roles_file",
        nargs="?",
        default=None,
        help="Path to the roles YAML file (default: roles/categories.yml at project root)",
    )
    parser.add_argument(
        "--suffix", "-s", help="Optional suffix to append to each path.", default=None
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--non-invokable",
        "-n",
        action="store_true",
        help="List paths where 'invokable' is False or not set.",
    )
    mode_group.add_argument(
        "--invokable",
        "-i",
        action="store_true",
        help="List paths where 'invokable' is True. (default behavior)",
    )

    args = parser.parse_args()

    repo_root = _project_root_from_here()

    # Ensure repo root on PYTHONPATH so 'filter_plugins' can be imported
    sys.path.insert(0, str(repo_root))

    from filter_plugins.invokable_paths import (
        get_invokable_paths,
        get_non_invokable_paths,
    )

    roles_file = args.roles_file or _default_roles_file()

    list_non = args.non_invokable

    try:
        if list_non:
            paths = get_non_invokable_paths(roles_file, args.suffix)
        else:
            paths = get_invokable_paths(roles_file, args.suffix)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
