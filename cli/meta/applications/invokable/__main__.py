#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from filter_plugins.get_all_invokable_apps import get_all_invokable_apps  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List all invokable applications (application_ids) based on invokable paths from categories.yml and available roles."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    try:
        result = get_all_invokable_apps()
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(result, indent=2))
        return

    for app_id in result:
        print(app_id)


if __name__ == "__main__":
    main()
