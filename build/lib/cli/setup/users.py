#!/usr/bin/env python3
import os
import sys
import argparse
import yaml
import glob
from collections import OrderedDict


def represent_str(dumper, data):
    """
    Custom YAML string representer that forces double quotes around any string
    containing a Jinja2 placeholder ({{ ... }}).
    """
    if isinstance(data, str) and '{{' in data:
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str',
            data,
            style='"'
        )
    return dumper.represent_scalar(
        'tag:yaml.org,2002:str',
        data
    )


def build_users(defs, primary_domain, start_id, become_pwd):
    """
    Construct user entries with auto-incremented UID/GID, default username/email,
    and optional description.

    Args:
        defs (OrderedDict): Mapping of user keys to their override settings.
        primary_domain (str): The primary domain for email addresses (e.g. 'example.com').
        start_id (int): Starting number for UID/GID allocation (e.g. 1001).
        become_pwd (str): Default password string for users without an override.

    Returns:
        OrderedDict: Complete user definitions with all required fields filled in.

    Raises:
        ValueError: If there are duplicate UIDs, usernames, or emails.
    """
    users = OrderedDict()
    used_uids = set()

    # Collect any preset UIDs to avoid collisions
    for key, overrides in defs.items():
        if 'uid' in overrides:
            uid = overrides['uid']
            if uid in used_uids:
                raise ValueError(f"Duplicate uid {uid} for user '{key}'")
            used_uids.add(uid)

    next_uid = start_id
    def allocate_uid():
        nonlocal next_uid
        # Find the next free UID not already used
        while next_uid in used_uids:
            next_uid += 1
        free_uid = next_uid
        used_uids.add(free_uid)
        next_uid += 1
        return free_uid

    # Build each user entry
    for key, overrides in defs.items():
        username = overrides.get('username', key)
        email = overrides.get('email', f"{username}@{primary_domain}")
        description = overrides.get('description')
        roles = overrides.get('roles', [])
        password = overrides.get('password', become_pwd)
        reserved = overrides.get('reserved', False) 

        # Determine UID and GID
        if 'uid' in overrides:
            uid = overrides['uid']
        else:
            uid = allocate_uid()
        gid = overrides.get('gid', uid)

        entry = {
            'username': username,
            'email': email,
            'password': password,
            'uid': uid,
            'gid': gid,
            'roles': roles
        }
        if description is not None:
            entry['description'] = description

        if reserved:
            entry['reserved'] = reserved

        users[key] = entry

    # Ensure uniqueness of usernames and emails
    seen_usernames = set()
    seen_emails = set()

    for key, entry in users.items():
        un = entry['username']
        em = entry['email']
        if un in seen_usernames:
            raise ValueError(f"Duplicate username '{un}' in merged users")
        if em in seen_emails:
            raise ValueError(f"Duplicate email '{em}' in merged users")
        seen_usernames.add(un)
        seen_emails.add(em)

    return users


def load_user_defs(roles_directory):
    """
    Scan all roles/*/users/main.yml files and merge any 'users:' sections.

    Args:
        roles_directory (str): Path to the directory containing role subdirectories.

    Returns:
        OrderedDict: Merged user definitions from all roles.

    Raises:
        ValueError: On invalid format or conflicting override values.
    """
    pattern = os.path.join(roles_directory, '*/users/main.yml')
    files = sorted(glob.glob(pattern))
    merged = OrderedDict()

    for filepath in files:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f) or {}
        users = data.get('users', {})
        if not isinstance(users, dict):
            continue

        for key, overrides in users.items():
            if not isinstance(overrides, dict):
                raise ValueError(f"Invalid definition for user '{key}' in {filepath}")

            if key not in merged:
                merged[key] = overrides.copy()
            else:
                existing = merged[key]
                for field, value in overrides.items():
                    if field in existing and existing[field] != value:
                        raise ValueError(
                            f"Conflict for user '{key}': field '{field}' has existing value '{existing[field]}', tried to set '{value}' in {filepath}"
                        )
                existing.update(overrides)

    return merged


def dictify(data):
    """
    Recursively convert OrderedDict to regular dict for YAML dumping.
    """
    if isinstance(data, OrderedDict):
        return {k: dictify(v) for k, v in data.items()}
    if isinstance(data, dict):
        return {k: dictify(v) for k, v in data.items()}
    if isinstance(data, list):
        return [dictify(v) for v in data]
    return data


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a users.yml by merging all roles/*/users/main.yml definitions.'
    )
    parser.add_argument(
        '--roles-dir', '-r', required=True,
        help='Directory containing roles (e.g., roles/*/users/main.yml).'
    )
    parser.add_argument(
        '--output', '-o', required=True,
        help='Path to the output YAML file (e.g., users.yml).'
    )
    parser.add_argument(
        '--start-id', '-s', type=int, default=1001,
        help='Starting UID/GID number (default: 1001).'
    )
    parser.add_argument(
        '--reserved-usernames', '-e',
        help='Comma-separated list of usernames to reserve.',
        default=None
    )
    return parser.parse_args()


def main():
    args = parse_args()
    primary_domain = '{{ SYSTEM_EMAIL.DOMAIN }}'
    become_pwd = '{{ lookup("password", "/dev/null length=42 chars=ascii_letters,digits") }}'

    try:
        definitions = load_user_defs(args.roles_dir)
    except ValueError as e:
        print(f"Error merging user definitions: {e}", file=sys.stderr)
        sys.exit(1)

    # Add reserved/ users if specified
    if args.reserved_usernames:
        for name in args.reserved_usernames.split(','):
            user_key = name.strip()
            if not user_key:
                continue
            if user_key in definitions:
                print(
                    f"Warning: reserved user '{user_key}' already defined; skipping (not changing existing definition).",
                    file=sys.stderr
                )
            else:
                definitions[user_key] = {}
            # Mark user as reserved
            definitions[user_key]["reserved"] = True
    try:
        users = build_users(
            definitions,
            primary_domain,
            args.start_id,
            become_pwd
        )
    except ValueError as e:
        print(f"Error building user entries: {e}", file=sys.stderr)
        sys.exit(1)

    # Sort users by key for deterministic output
    if isinstance(users, dict) and users:
        users = OrderedDict(sorted(users.items()))

    # Convert OrderedDict into plain dict for YAML
    default_users = {'default_users': users}
    plain_data = dictify(default_users)

    # Register custom string representer
    yaml.SafeDumper.add_representer(str, represent_str)

    # Dump the YAML file
    with open(args.output, 'w') as f:
        yaml.safe_dump(
            plain_data,
            f,
            default_flow_style=False,
            sort_keys=False,
            width=120
        )

if __name__ == '__main__':
    main()
