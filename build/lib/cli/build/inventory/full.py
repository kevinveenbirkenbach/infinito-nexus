#!/usr/bin/env python3
# cli/build/inventory/full.py

import argparse
import sys
import os

try:
    from filter_plugins.get_all_invokable_apps import get_all_invokable_apps
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
    from filter_plugins.get_all_invokable_apps import get_all_invokable_apps

import yaml
import json

def build_group_inventory(apps, host):
    """
    Build an Ansible inventory in which each application is a group containing the given host.
    """
    groups = {app: {"hosts": [host]} for app in apps}
    inventory = {
        "all": {
            "hosts": [host],
            "children": {app: {} for app in apps},
        },
        **groups
    }
    return inventory

def build_hostvar_inventory(apps, host):
    """
    Alternative: Build an inventory where all invokable apps are set as a host variable (as a list).
    """
    return {
        "all": {
            "hosts": [host],
        },
        "_meta": {
            "hostvars": {
                host: {
                    "invokable_applications": apps
                }
            }
        }
    }

def main():
    parser = argparse.ArgumentParser(
        description='Build a dynamic Ansible inventory for a given host with all invokable applications.'
    )
    parser.add_argument(
        '--host',
        required=True,
        help='Hostname to assign to all invokable application groups'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'yaml'],
        default='yaml',
        help='Output format (yaml [default], json)'
    )
    parser.add_argument(
        '--inventory-style',
        choices=['group', 'hostvars'],
        default='group',
        help='Inventory style: group (default, one group per app) or hostvars (list as hostvar)'
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
    parser.add_argument(
        '-o', '--output',
        help='Write output to file instead of stdout'
    )
    parser.add_argument(
        '-i', '--ignore',
        action='append',
        default=[],
        help='Application ID(s) to ignore (can be specified multiple times or comma-separated)'
    )
    args = parser.parse_args()

    try:
        apps = get_all_invokable_apps(
            categories_file=args.categories_file,
            roles_dir=args.roles_dir
        )
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    # Combine all ignore arguments into a flat set
    ignore_ids = set()
    for entry in args.ignore:
        ignore_ids.update(i.strip() for i in entry.split(',') if i.strip())

    if ignore_ids:
        apps = [app for app in apps if app not in ignore_ids]

    # Build the requested inventory style
    if args.inventory_style == 'group':
        inventory = build_group_inventory(apps, args.host)
    else:
        inventory = build_hostvar_inventory(apps, args.host)

    # Output in the chosen format
    if args.format == 'json':
        output = json.dumps(inventory, indent=2)
    else:
        output = yaml.safe_dump(inventory, default_flow_style=False)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)

if __name__ == '__main__':
    main()
