#!/usr/bin/env python3
from __future__ import annotations

import argparse

from .resolver import CombinedResolver
from .tree import print_tree


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve run_after + dependencies transitively for a role (optional tree output)."
    )
    parser.add_argument(
        "role_name", help="Name of the role folder under ./roles (e.g., web-app-taiga)"
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Print an ASCII dependency tree instead of a whitespace-separated list.",
    )
    args = parser.parse_args()

    if args.tree:
        print_tree(args.role_name)
        return

    resolver = CombinedResolver()
    resolved = resolver.resolve(args.role_name)
    print(" ".join(resolved))


if __name__ == "__main__":
    main()
