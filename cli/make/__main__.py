#!/usr/bin/env python3
"""
CLI wrapper for Makefile targets within Infinito.Nexus.
Invokes `make` commands in the project root directory.
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="infinito make",
        description="Run Makefile targets for Infinito.Nexus project",
    )
    parser.add_argument(
        "targets",
        nargs=argparse.REMAINDER,
        help="Make targets and options to pass to `make`",
    )
    args = parser.parse_args()

    # Default to 'build' if no target is specified
    make_args = args.targets or ["build"]

    from . import PROJECT_ROOT

    repo_root = str(PROJECT_ROOT)

    # Check for Makefile
    makefile_path = os.path.join(repo_root, "Makefile")
    if not os.path.isfile(makefile_path):
        print(f"Error: Makefile not found in {repo_root}", file=sys.stderr)
        sys.exit(1)

    # Invoke make in repo root
    cmd = ["make", *make_args]
    try:
        result = subprocess.run(cmd, cwd=repo_root)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("Error: 'make' command not found. Please install make.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
