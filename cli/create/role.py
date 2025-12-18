#!/usr/bin/env python3
import argparse
import shutil
import ipaddress
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ruamel.yaml import YAML

import sys
import os
from module_utils.entity_name_utils import get_entity_name

# Paths to the group-vars files
PORTS_FILE = "./group_vars/all/10_ports.yml"
NETWORKS_FILE = "./group_vars/all/09_networks.yml"
ROLE_TEMPLATE_DIR = "./templates/roles/web-app"
ROLES_DIR = "./roles"

yaml = YAML()
yaml.preserve_quotes = True


def load_yaml_with_comments(path):
    with open(path) as f:
        return yaml.load(f)


def dump_yaml_with_comments(data, path):
    with open(path, "w") as f:
        yaml.dump(data, f)


def get_next_network(networks_dict, prefixlen):
    """Select the next contiguous subnet, based on the highest existing subnet + one network offset."""
    nets = []
    local = networks_dict["defaults_networks"]["local"]
    for name, info in local.items():
        # info is a dict with 'subnet' key
        net = ipaddress.ip_network(info["subnet"])
        if net.prefixlen == prefixlen:
            nets.append(net)
    if not nets:
        raise RuntimeError(f"No existing /{prefixlen} subnets to base allocation on.")
    nets.sort(key=lambda n: int(n.network_address))
    last = nets[-1]
    offset = last.num_addresses
    next_net = ipaddress.ip_network((int(last.network_address) + offset, prefixlen))
    return next_net


def get_next_port(ports_dict, category):
    """Assign the next port by taking the max existing plus one."""
    loc = ports_dict["ports"]["localhost"][category]
    existing = [int(v) for v in loc.values()]
    return (max(existing) + 1) if existing else 1


def prompt_conflict(dst_file):
    print(f"Conflict detected: {dst_file}")
    print("[1] overwrite, [2] skip, [3] merge")
    choice = None
    while choice not in ("1", "2", "3"):
        choice = input("Enter 1, 2, or 3: ").strip()
    return choice


def render_templates(src_dir, dst_dir, context):
    env = Environment(
        loader=FileSystemLoader(src_dir), keep_trailing_newline=True,
        autoescape=select_autoescape(['html', 'xml'])
    )
    env.filters["bool"] = lambda x: bool(x)
    env.filters["get_entity_name"] = get_entity_name

    for root, _, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        target = os.path.join(dst_dir, rel)
        os.makedirs(target, exist_ok=True)
        for fn in files:
            tpl = env.get_template(os.path.join(rel, fn))
            rendered = tpl.render(**context)
            out = fn[:-3] if fn.endswith(".j2") else fn
            dst_file = os.path.join(target, out)

            if os.path.exists(dst_file):
                choice = prompt_conflict(dst_file)
                if choice == "2":
                    print(f"Skipping {dst_file}")
                    continue
                if choice == "3":
                    with open(dst_file) as f_old:
                        old_lines = f_old.readlines()
                    new_lines = rendered.splitlines(keepends=True)
                    additions = [line for line in new_lines if line not in old_lines]
                    if additions:
                        with open(dst_file, "a") as f:
                            f.writelines(additions)
                        print(f"Merged {len(additions)} lines into {dst_file}")
                    else:
                        print(f"No new lines to merge into {dst_file}")
                    continue
                # overwrite
                print(f"Overwriting {dst_file}")
                with open(dst_file, "w") as f:
                    f.write(rendered)
            else:
                # create new file
                with open(dst_file, "w") as f:
                    f.write(rendered)


def main():
    # Load dynamic port categories
    ports_data = load_yaml_with_comments(PORTS_FILE)
    categories = list(ports_data["ports"]["localhost"].keys())

    parser = argparse.ArgumentParser(
        description="Create or update a Docker Ansible role, and globally assign network and ports with comments preserved"
    )
    parser.add_argument(
        "-a", "--application-id", required=True, help="Unique application ID"
    )
    parser.add_argument(
        "-n",
        "--network",
        choices=["24", "28"],
        required=True,
        help="Network prefix length (/24 or /28)",
    )
    parser.add_argument(
        "-p",
        "--ports",
        nargs="+",
        choices=categories,
        required=True,
        help=f"Port categories to assign (allowed: {', '.join(categories)})",
    )
    args = parser.parse_args()

    app = args.application_id
    role = f"web-app-{app}"
    role_dir = os.path.join(ROLES_DIR, role)

    if os.path.exists(role_dir):
        if input(f"Role {role} exists. Continue? [y/N]: ").strip().lower() != "y":
            print("Aborting.")
            sys.exit(1)
    else:
        os.makedirs(role_dir)

    # 1) Render all templates with conflict handling
    render_templates(
        ROLE_TEMPLATE_DIR,
        role_dir,
        {"application_id": app, "role_name": role, "database_type": 0},
    )
    print(f"→ Templates applied to {role_dir}")

    # 2) Update global networks file, preserving comments
    networks = load_yaml_with_comments(NETWORKS_FILE)
    prefix = int(args.network)
    new_net = get_next_network(networks, prefix)
    networks["defaults_networks"]["local"][app] = {"subnet": str(new_net)}
    shutil.copy(NETWORKS_FILE, NETWORKS_FILE + ".bak")
    dump_yaml_with_comments(networks, NETWORKS_FILE)
    print(f"→ Assigned network {new_net} in {NETWORKS_FILE}")

    # 3) Update global ports file, preserving comments
    ports_data = load_yaml_with_comments(PORTS_FILE)
    assigned = {}
    for cat in args.ports:
        loc = ports_data["ports"]["localhost"].setdefault(cat, {})
        if app in loc:
            print(f"→ Existing port for {cat} and {app}: {loc[app]}, skipping.")
        else:
            pnum = get_next_port(ports_data, cat)
            loc[app] = pnum
            assigned[cat] = pnum

    if assigned:
        shutil.copy(PORTS_FILE, PORTS_FILE + ".bak")
        dump_yaml_with_comments(ports_data, PORTS_FILE)
        print(f"→ Assigned ports {assigned} in {PORTS_FILE}")
    else:
        print("→ No new ports assigned.")


if __name__ == "__main__":
    main()
