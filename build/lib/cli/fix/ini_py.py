#!/usr/bin/env python3

"""
This script creates __init__.py files in every subdirectory under the specified
folder relative to the project root.
"""

import os
import argparse


def create_init_files(root_folder):
    """
    Walk through all subdirectories of root_folder and create an __init__.py file
    in each directory if it doesn't already exist.
    """
    for dirpath, dirnames, filenames in os.walk(root_folder):
        init_file = os.path.join(dirpath, '__init__.py')
        if not os.path.exists(init_file):
            open(init_file, 'w').close()
            print(f"Created: {init_file}")
        else:
            print(f"Skipped (already exists): {init_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Create __init__.py files in every subdirectory.'
    )
    parser.add_argument(
        'folder',
        help='Relative path to the target folder (e.g., cli/fix)'
    )
    args = parser.parse_args()

    # Determine the absolute path based on the current working directory
    root_folder = os.path.abspath(args.folder)

    if not os.path.isdir(root_folder):
        print(f"Error: The folder '{args.folder}' does not exist or is not a directory.")
        exit(1)

    create_init_files(root_folder)


if __name__ == '__main__':
    main()
