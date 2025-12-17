#!/usr/bin/env python3
# cli/meta/applications/invokable.py

import argparse
import sys
import os

# Import filter plugin for get_all_invokable_apps
try:
    from filter_plugins.get_all_invokable_apps import get_all_invokable_apps
except ImportError:
    # Try to adjust sys.path if running outside Ansible
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
    try:
        from filter_plugins.get_all_invokable_apps import get_all_invokable_apps
    except ImportError:
        sys.stderr.write("Could not import filter_plugins.get_all_invokable_apps. Check your PYTHONPATH.\n")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='List all invokable applications (application_ids) based on invokable paths from categories.yml and available roles.'
    )
    parser.add_argument(
        '-c', '--categories-file',
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'roles', 'categories.yml')),
        help='Path to roles/categories.yml (default: roles/categories.yml at project root)'
    )
    parser.add_argument(
        '-r', '--roles-dir',
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'roles')),
        help='Path to roles/ directory (default: roles/ at project root)'
    )
    args = parser.parse_args()

    try:
        result = get_all_invokable_apps(
            categories_file=args.categories_file,
            roles_dir=args.roles_dir
        )
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    for app_id in result:
        print(app_id)

if __name__ == '__main__':
    main()
