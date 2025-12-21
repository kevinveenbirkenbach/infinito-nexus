#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from filter_plugins.get_all_invokable_apps import get_all_invokable_apps  # noqa: E402
 

def main():
    parser = argparse.ArgumentParser(
        description="List all invokable applications (application_ids) based on invokable paths from categories.yml and available roles."
    )
    parser.add_argument(
        "-c",
        "--categories-file",
        default=str(REPO_ROOT / "roles" / "categories.yml"),
        help="Path to roles/categories.yml (default: roles/categories.yml at project root)",
    )
    parser.add_argument(
        "-r",
        "--roles-dir",
        default=str(REPO_ROOT / "roles"),
        help="Path to roles/ directory (default: roles/ at project root)",
    )
    args = parser.parse_args()

    try:
        result = get_all_invokable_apps(
            categories_file=args.categories_file, roles_dir=args.roles_dir
        )
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    for app_id in result:
        print(app_id)


if __name__ == "__main__":
    main()
