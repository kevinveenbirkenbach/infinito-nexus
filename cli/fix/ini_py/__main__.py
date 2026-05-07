#!/usr/bin/env python3

"""
This script creates __init__.py files in every subdirectory under the specified
folder relative to the project root.
"""

import argparse
import os
import sys
from pathlib import Path


def create_init_files(root_folder):
    """
    Walk through all subdirectories of root_folder and create an __init__.py file
    in each directory if it doesn't already exist.
    """
    for dirpath, _dirnames, _filenames in os.walk(root_folder):
        init_file = str(Path(dirpath) / "__init__.py")
        if not Path(init_file).exists():
            Path(init_file).open("w").close()
            print(f"Created: {init_file}")
        else:
            print(f"Skipped (already exists): {init_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Create __init__.py files in every subdirectory."
    )
    parser.add_argument(
        "folder", help="Relative path to the target folder (e.g., cli/fix)"
    )
    args = parser.parse_args()

    # Determine the absolute path based on the current working directory
    root_folder = str(Path(args.folder).resolve())

    if not Path(root_folder).is_dir():
        print(
            f"Error: The folder '{args.folder}' does not exist or is not a directory."
        )
        sys.exit(1)

    create_init_files(root_folder)


if __name__ == "__main__":
    main()
