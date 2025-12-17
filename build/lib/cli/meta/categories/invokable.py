#!/usr/bin/env python3
"""
CLI for extracting invokable or non-invokable role paths from a nested roles YAML file using argparse.
Assumes a default roles file at the project root if none is provided.
"""

import os
import sys

# ─── Determine project root ───
if "__file__" in globals():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    project_root = os.getcwd()

# Ensure project root on PYTHONPATH so 'filter_plugins' can be imported
sys.path.insert(0, project_root)

import argparse
import yaml
from filter_plugins.invokable_paths import get_invokable_paths, get_non_invokable_paths


def main():
    parser = argparse.ArgumentParser(
        description="Extract invokable or non-invokable role paths from a nested roles YAML file."
    )
    parser.add_argument(
        "roles_file",
        nargs='?',
        default=None,
        help="Path to the roles YAML file (default: roles/categories.yml at project root)"
    )
    parser.add_argument(
        "--suffix", "-s",
        help="Optional suffix to append to each path.",
        default=None
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--non-invokable", "-n",
        action='store_true',
        help="List paths where 'invokable' is False or not set."
    )
    mode_group.add_argument(
        "--invokable", "-i",
        action='store_true',
        help="List paths where 'invokable' is True. (default behavior)"
    )

    args = parser.parse_args()

    # Default to invokable if neither flag is provided
    list_non = args.non_invokable
    list_inv = args.invokable or not (args.non_invokable or args.invokable)

    try:
        if list_non:
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

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
