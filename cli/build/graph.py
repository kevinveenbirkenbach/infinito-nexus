#!/usr/bin/env python3
import os
import argparse
import yaml
import json
import re
from typing import List, Dict, Any, Set


JINJA_PATTERN = re.compile(r'{{.*}}')
ALL_DEP_TYPES = ['run_after', 'dependencies', 'include_tasks', 'import_tasks', 'include_role', 'import_role']
ALL_DIRECTIONS = ['to', 'from']
ALL_KEYS = [f"{dep}_{dir}" for dep in ALL_DEP_TYPES for dir in ALL_DIRECTIONS]


def find_role_meta(roles_dir: str, role: str) -> str:
    path = os.path.join(roles_dir, role, 'meta', 'main.yml')
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Metadata not found for role: {role}")
    return path


def find_role_tasks(roles_dir: str, role: str) -> str:
    path = os.path.join(roles_dir, role, 'tasks', 'main.yml')
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Tasks not found for role: {role}")
    return path


def load_meta(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or {}

    galaxy_info = data.get('galaxy_info', {}) or {}
    return {
        'galaxy_info': galaxy_info,
        'run_after': galaxy_info.get('run_after', []) or [],
        'dependencies': data.get('dependencies', []) or []
    }


def load_tasks(path: str, dep_type: str) -> List[str]:
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or []

    included_roles = []

    for task in data:
        if dep_type in task:
            entry = task[dep_type]
            if isinstance(entry, dict):
                entry = entry.get('name', '')
            if entry and not JINJA_PATTERN.search(entry):
                included_roles.append(entry)

    return included_roles


def build_single_graph(
    start_role: str,
    dep_type: str,
    direction: str,
    roles_dir: str,
    max_depth: int
) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, str]] = []

    def traverse(role: str, depth: int, path: Set[str]):
        if role not in nodes:
            meta = load_meta(find_role_meta(roles_dir, role))
            node = {'id': role}
            node.update(meta['galaxy_info'])
            node['doc_url'] = f"https://docs.infinito.nexus/roles/{role}/README.html"
            node['source_url'] = f"https://s.infinito.nexus/code/tree/master/roles/{role}"
            nodes[role] = node

        if max_depth > 0 and depth >= max_depth:
            return

        neighbors = []
        if dep_type in ['run_after', 'dependencies']:
            meta = load_meta(find_role_meta(roles_dir, role))
            neighbors = meta.get(dep_type, [])
        else:
            try:
                neighbors = load_tasks(find_role_tasks(roles_dir, role), dep_type)
            except FileNotFoundError:
                neighbors = []

        if direction == 'to':
            for tgt in neighbors:
                links.append({'source': role, 'target': tgt, 'type': dep_type})
                if tgt in path:
                    continue
                traverse(tgt, depth + 1, path | {tgt})

        else:  # direction == 'from'
            for other in os.listdir(roles_dir):
                try:
                    other_neighbors = []
                    if dep_type in ['run_after', 'dependencies']:
                        meta_o = load_meta(find_role_meta(roles_dir, other))
                        other_neighbors = meta_o.get(dep_type, [])
                    else:
                        other_neighbors = load_tasks(find_role_tasks(roles_dir, other), dep_type)

                    if role in other_neighbors:
                        links.append({'source': other, 'target': role, 'type': dep_type})
                        if other in path:
                            continue
                        traverse(other, depth + 1, path | {other})

                except FileNotFoundError:
                    continue

    traverse(start_role, depth=0, path={start_role})
    return {'nodes': list(nodes.values()), 'links': links}


def build_mappings(
    start_role: str,
    roles_dir: str,
    max_depth: int
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key in ALL_KEYS:
        dep_type, direction = key.rsplit('_', 1)
        try:
            result[key] = build_single_graph(start_role, dep_type, direction, roles_dir, max_depth)
        except Exception:
            result[key] = {'nodes': [], 'links': []}
    return result


def output_graph(graph_data: Any, fmt: str, start: str, key: str):
    base = f"{start}_{key}"
    if fmt == 'console':
        print(f"--- {base} ---")
        print(yaml.safe_dump(graph_data, sort_keys=False))
    elif fmt in ('yaml', 'json'):
        path = f"{base}.{fmt}"
        with open(path, 'w') as f:
            if fmt == 'yaml':
                yaml.safe_dump(graph_data, f, sort_keys=False)
            else:
                json.dump(graph_data, f, indent=2)
        print(f"Wrote {path}")
    else:
        raise ValueError(f"Unknown format: {fmt}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_roles_dir = os.path.abspath(os.path.join(script_dir, '..', '..', 'roles'))

    parser = argparse.ArgumentParser(description="Generate dependency graphs")
    parser.add_argument('-r', '--role', required=True, help="Starting role name")
    parser.add_argument('-D', '--depth', type=int, default=0, help="Max recursion depth")
    parser.add_argument('-o', '--output', choices=['yaml', 'json', 'console'], default='console')
    parser.add_argument('--roles-dir', default=default_roles_dir, help="Roles directory")

    args = parser.parse_args()

    graphs = build_mappings(args.role, args.roles_dir, args.depth)

    for key in ALL_KEYS:
        graph_data = graphs.get(key, {'nodes': [], 'links': []})
        output_graph(graph_data, args.output, args.role, key)


if __name__ == '__main__':
    main()
