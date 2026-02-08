#!/usr/bin/env python3
"""
CLI for extracting invokable or non-invokable role paths from a nested roles YAML file.

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

# IMPORTANT:
# These imports must exist at module level so unittest.mock.patch()
# can replace them in tests.
from filter_plugins.invokable_paths import (
    get_invokable_paths,
    get_non_invokable_paths,
)


def _project_root_from_here() -> Path:
    """
    Determine repo root by fixed parent depth.
    command.py -> invokable -> categories -> meta -> cli -> repo_root
    """
    return Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract invokable or non-invokable role paths from a nested roles YAML file."
    )

    parser.add_argument(
        "roles_file",
        nargs="?",
        default=None,
        help="Path to roles/categories.yml (optional).",
    )

    parser.add_argument(
        "--suffix",
        "-s",
        default=None,
        help="Optional suffix to append to each path.",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--non-invokable",
        "-n",
        action="store_true",
        help="List non-invokable paths.",
    )
    mode.add_argument(
        "--invokable",
        "-i",
        action="store_true",
        help="List invokable paths (default).",
    )

    args = parser.parse_args()

    # Ensure repo root is importable (CLI use outside repo root)
    repo_root = _project_root_from_here()
    sys.path.insert(0, str(repo_root))

    try:
        if args.non_invokable:
            paths = get_non_invokable_paths(args.roles_file, args.suffix)
        else:
            paths = get_invokable_paths(args.roles_file, args.suffix)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
