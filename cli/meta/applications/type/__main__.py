#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from module_utils.invokable import list_invokables_by_type  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List invokable applications grouped by deployment type (server/workstation/universal)."
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=("server", "workstation", "universal"),
        help="Return only the list for a single deployment type",
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
        grouped = list_invokables_by_type()
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    if args.type:
        apps = grouped.get(args.type, [])
        if args.format == "json":
            print(json.dumps(apps, indent=2))
            return
        for app_id in apps:
            print(app_id)
        return

    if args.format == "json":
        print(json.dumps(grouped, indent=2, sort_keys=True))
        return

    # text
    for t in ("server", "workstation", "universal"):
        apps = grouped.get(t, [])
        print(f"[{t}]")
        for app_id in apps:
            print(app_id)
        print("")


if __name__ == "__main__":
    main()
