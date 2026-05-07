#!/usr/bin/env python3

import argparse
from pathlib import Path

FILES_FIXED = []


def fix_tabs_in_file(file_path):
    """Replaces tab characters with two spaces in the specified file."""
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if any("\t" in line for line in lines):
        fixed_lines = [line.replace("\t", "  ") for line in lines]
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(fixed_lines)
        FILES_FIXED.append(str(file_path))


def find_yml_files(path):
    """Yield all .yml files under a given path recursively."""
    for file in path.rglob("*.yml"):
        if file.is_file():
            yield file


def main():
    parser = argparse.ArgumentParser(
        description="Fix tab characters in all .yml files under a given path (recursively)."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="./",
        help="Base path to search for .yml files (default: ./)",
    )
    args = parser.parse_args()

    base_path = Path(args.path).resolve()

    if not base_path.exists():
        print(f"❌ Path does not exist: {base_path}")
        exit(1)

    print(f"🔍 Searching for .yml files under: {base_path}\n")

    for yml_file in find_yml_files(base_path):
        fix_tabs_in_file(yml_file)

    if FILES_FIXED:
        print("✅ Fixed tab characters in the following files:")
        for f in FILES_FIXED:
            print(f"  - {f}")
    else:
        print("✅ No tabs found in any .yml files.")


if __name__ == "__main__":
    main()
