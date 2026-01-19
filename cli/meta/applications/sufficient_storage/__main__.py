#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is in PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from module_utils.role_resource_validation import filter_roles_by_min_storage  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate roles by services.docker.<entity>.min_storage in roles/*/config/main.yml"
    )

    parser.add_argument(
        "--roles",
        nargs="+",
        required=True,
        help="List of role names (directory names under roles/)",
    )

    parser.add_argument(
        "--required-storage",
        required=True,
        help="Required storage value (e.g. 80G, 1Ti, 500GB, 2 TB)",
    )

    parser.add_argument(
        "--warnings",
        action="store_true",
        help="Emit GitHub Actions warnings for missing configs/keys",
    )

    parser.add_argument(
        "--roles-root",
        default="roles",
        help="Roles root directory (default: roles)",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    matching = filter_roles_by_min_storage(
        role_names=args.roles,
        required_storage=args.required_storage,
        emit_warnings=args.warnings,
        roles_root=args.roles_root,
    )

    # Print space-separated for easy CI consumption
    if matching:
        print(" ".join(matching))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
