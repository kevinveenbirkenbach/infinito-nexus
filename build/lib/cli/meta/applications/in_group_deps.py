#!/usr/bin/env python3
"""
CLI wrapper for applications_if_group_and_deps filter.
"""
import argparse
import sys
import os
import yaml
from filter_plugins.applications_if_group_and_deps import FilterModule


def find_role_dirs_by_app_id(app_ids, roles_dir):
    """
    Map application_ids to role directory names based on vars/main.yml in each role.
    """
    mapping = {}
    for role in os.listdir(roles_dir):
        role_path = os.path.join(roles_dir, role)
        vars_file = os.path.join(role_path, 'vars', 'main.yml')
        if not os.path.isfile(vars_file):
            continue
        try:
            with open(vars_file) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        app_id = data.get('application_id')
        if isinstance(app_id, str) and app_id:
            mapping[app_id] = role
    # Translate each requested app_id to role dir if exists
    dirs = []
    for gid in app_ids:
        if gid in mapping:
            dirs.append(mapping[gid])
        else:
            # keep original if it matches a directory
            if os.path.isdir(os.path.join(roles_dir, gid)):
                dirs.append(gid)
    return dirs


def main():
    parser = argparse.ArgumentParser(
        description="Filter applications by group names (role dirs or application_ids) and their recursive role dependencies."
    )
    parser.add_argument(
        "-a", "--applications",
        type=str,
        required=True,
        help="Path to YAML file defining the applications dict."
    )
    parser.add_argument(
        "-g", "--groups",
        nargs='+',
        required=True,
        help="List of group names to filter by (role directory names or application_ids)."
    )
    args = parser.parse_args()

    # Load applications
    try:
        with open(args.applications) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading applications file: {e}", file=sys.stderr)
        sys.exit(1)

    # Unwrap under 'applications' key if present
    if isinstance(data, dict) and 'applications' in data and isinstance(data['applications'], dict):
        applications = data['applications']
    else:
        applications = data

    if not isinstance(applications, dict):
        print(
            f"Expected applications YAML to contain a mapping (or 'applications' mapping), got {type(applications).__name__}",
            file=sys.stderr
        )
        sys.exit(1)

    # Determine roles_dir relative to project root
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    roles_dir = os.path.join(project_root, 'roles')

    # Map user-provided groups (which may be application_ids) to role directory names
    group_dirs = find_role_dirs_by_app_id(args.groups, roles_dir)
    if not group_dirs:
        print(f"No matching role directories found for groups: {args.groups}", file=sys.stderr)
        sys.exit(1)

    # Run filter using role directory names
    try:
        filtered = FilterModule().applications_if_group_and_deps(
            applications,
            group_dirs
        )
    except Exception as e:
        print(f"Error running filter: {e}", file=sys.stderr)
        sys.exit(1)

    # Output result as YAML
    print(yaml.safe_dump(filtered, default_flow_style=False))


if __name__ == '__main__':
    main()
