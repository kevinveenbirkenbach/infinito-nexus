#!/usr/bin/env python3
import argparse
import sys
import yaml
import re
from pathlib import Path

# Ensure imports work when run directly
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
sys.path.insert(0, str(repo_root))

from cli.meta.applications.all import find_application_ids

def load_yaml_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            content = re.sub(r'(?m)^([ \t]*[^\s:]+):\s*!vault[\s\S]+?(?=^\S|\Z)', r"\1: \"<vaulted>\"\n", content)
            return yaml.safe_load(content)
    except Exception as e:
        print(f"Warning: Could not parse {path}: {e}", file=sys.stderr)
        return None


def recursive_keys(d, prefix=''):
    keys = set()
    if isinstance(d, dict):
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.add(full)
            keys.update(recursive_keys(v, full))
    return keys


def compare_application_keys(applications, defaults, source):
    errs = []
    for app_id, conf in applications.items():
        if app_id not in defaults:
            errs.append(f"{source}: Unknown application '{app_id}' (not in defaults_applications)")
            continue
        default = defaults[app_id]
        app_keys = recursive_keys(conf)
        def_keys = recursive_keys(default)
        for key in app_keys:
            if key.startswith('credentials'):
                continue
            if key not in def_keys:
                errs.append(f"{source}: Missing default for {app_id}: {key}")
    return errs


def compare_user_keys(users, default_users, source):
    errs = []
    for user, conf in users.items():
        if user not in default_users:
            print(f"Warning: {source}: Unknown user '{user}' (not in default_users)", file=sys.stderr)
            continue
        def_conf = default_users[user]
        for key in conf:
            if key in ('password','credentials','mailu_token'):
                continue
            if key not in def_conf:
                errs.append(f"Missing default for user '{user}': key '{key}'")
    return errs


def load_inventory_files(inv_dir):
    all_data = {}
    p = Path(inv_dir)
    for f in p.glob('*.yml'):
        data = load_yaml_file(f)
        if isinstance(data, dict):
            apps = data.get('applications') or data.get('defaults_applications')
            if apps:
                all_data[str(f)] = apps
    for d in p.glob('*_vars'):
        if d.is_dir():
            for f in d.rglob('*.yml'):
                data = load_yaml_file(f)
                if isinstance(data, dict):
                    apps = data.get('applications') or data.get('defaults_applications')
                    if apps:
                        all_data[str(f)] = apps
    return all_data


def validate_host_keys(app_ids, inv_dir):
    errs = []
    p = Path(inv_dir)
    # Scan all top-level YAMLs for 'all.children'
    for f in p.glob('*.yml'):
        data = load_yaml_file(f)
        if not isinstance(data, dict):
            continue
        all_node = data.get('all', {})
        children = all_node.get('children')
        if not isinstance(children, dict):
            continue
        for grp in children.keys():
            if grp not in app_ids:
                errs.append(f"{f}: Invalid group '{grp}' (not in application_ids)")
    return errs


def find_single_file(pattern):
    c = list(Path('group_vars/all').glob(pattern))
    if len(c)!=1:
        raise RuntimeError(f"Expected exactly one {pattern} in group_vars/all, found {len(c)}")
    return c[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('inventory_dir')
    args = p.parse_args()
    # defaults
    dfile = find_single_file('*_applications.yml')
    ufile = find_single_file('*users.yml')
    ddata = load_yaml_file(dfile) or {}
    udata = load_yaml_file(ufile) or {}
    defaults = ddata.get('defaults_applications',{})
    default_users = udata.get('default_users',{})
    if not defaults:
        print(f"Error: No 'defaults_applications' found in {dfile}", file=sys.stderr)
        sys.exit(1)
    if not default_users:
        print(f"Error: No 'default_users' found in {ufile}", file=sys.stderr)
        sys.exit(1)
    app_errs = []
    inv_files = load_inventory_files(args.inventory_dir)
    for src, apps in inv_files.items():
        app_errs.extend(compare_application_keys(apps, defaults, src))
    user_errs = []
    for fpath in Path(args.inventory_dir).rglob('*.yml'):
        data = load_yaml_file(fpath)
        if isinstance(data, dict) and 'users' in data:
            errs = compare_user_keys(data['users'], default_users, str(fpath))
            for e in errs:
                print(e, file=sys.stderr)
            user_errs.extend(errs)
    host_errs = validate_host_keys(find_application_ids(), args.inventory_dir)
    app_errs.extend(host_errs)
    if app_errs or user_errs:
        if app_errs:
            print('Validation failed with the following issues:')
            for e in app_errs:
                print(f"- {e}")
        sys.exit(1)
    print('Inventory directory is valid against defaults and hosts.')
    sys.exit(0)

if __name__=='__main__':
    main()
