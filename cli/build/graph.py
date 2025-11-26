#!/usr/bin/env python3
import os
import argparse
import yaml
import json
import re
from typing import List, Dict, Any, Set

from module_utils.role_dependency_resolver import RoleDependencyResolver

# Regex used to ignore Jinja expressions inside include/import statements
JINJA_PATTERN = re.compile(r'{{.*}}')

# All dependency types the graph builder supports
ALL_DEP_TYPES = [
    "run_after",
    "dependencies",
    "include_tasks",
    "import_tasks",
    "include_role",
    "import_role",
]

# Graph directions: outgoing edges ("to") vs incoming edges ("from")
ALL_DIRECTIONS = ["to", "from"]

# Combined keys: e.g. "include_role_to", "dependencies_from", etc.
ALL_KEYS = [f"{dep}_{direction}" for dep in ALL_DEP_TYPES for direction in ALL_DIRECTIONS]


# ------------------------------------------------------------
# Helpers for locating meta and task files
# ------------------------------------------------------------

def find_role_meta(roles_dir: str, role: str) -> str:
    """Return path to meta/main.yml of a role or raise FileNotFoundError."""
    path = os.path.join(roles_dir, role, "meta", "main.yml")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Metadata not found for role: {role}")
    return path


def find_role_tasks(roles_dir: str, role: str) -> str:
    """Return path to tasks/main.yml of a role or raise FileNotFoundError."""
    path = os.path.join(roles_dir, role, "tasks", "main.yml")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Tasks not found for role: {role}")
    return path


# ------------------------------------------------------------
# Parsers for meta and tasks
# ------------------------------------------------------------

def load_meta(path: str) -> Dict[str, Any]:
    """
    Load metadata from meta/main.yml.
    Returns a dict with:
        - galaxy_info
        - run_after
        - dependencies
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    galaxy_info = data.get("galaxy_info", {}) or {}
    return {
        "galaxy_info": galaxy_info,
        "run_after": galaxy_info.get("run_after", []) or [],
        "dependencies": data.get("dependencies", []) or [],
    }


def load_tasks(path: str, dep_type: str) -> List[str]:
    """
    Parse include_tasks/import_tasks from tasks/main.yml.
    Only accepts simple, non-Jinja names.
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f) or []

    roles: List[str] = []

    for task in data:
        if not isinstance(task, dict):
            continue

        if dep_type in task:
            entry = task[dep_type]
            if isinstance(entry, dict):
                entry = entry.get("name", "")
            if isinstance(entry, str) and entry and not JINJA_PATTERN.search(entry):
                roles.append(entry)

    return roles


# ------------------------------------------------------------
# Graph builder using precomputed caches (fast)
# ------------------------------------------------------------

def build_single_graph(
    start_role: str,
    dep_type: str,
    direction: str,
    roles_dir: str,
    max_depth: int,
    caches: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a graph (nodes + links) for one role, one dep_type, one direction.
    Uses only precomputed in-memory caches, no filesystem access.

    caches structure:
        caches["meta"][role]                        -> meta information
        caches["deps"][dep_type][role]              -> outgoing targets
        caches["rev"][dep_type][target]             -> set of source roles
    """

    nodes: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, str]] = []

    meta_cache = caches["meta"]
    deps_cache = caches["deps"]
    rev_cache = caches["rev"]

    # --------------------------------------------------------
    # Ensure a role exists as a node
    # --------------------------------------------------------
    def ensure_node(role: str):
        if role in nodes:
            return

        # Try retrieving cached meta; fallback: lazy load
        meta = meta_cache.get(role)
        if meta is None:
            try:
                meta = load_meta(find_role_meta(roles_dir, role))
                meta_cache[role] = meta
            except FileNotFoundError:
                meta = {"galaxy_info": {}}

        galaxy_info = meta.get("galaxy_info", {}) or {}

        node = {
            "id": role,
            **galaxy_info,
            "doc_url": f"https://docs.infinito.nexus/roles/{role}/README.html",
            "source_url": f"https://github.com/kevinveenbirkenbach/infinito-nexus/tree/master/roles/{role}",
        }
        nodes[role] = node

    # --------------------------------------------------------
    # Outgoing edges: role -> targets
    # --------------------------------------------------------
    def outgoing(role: str) -> List[str]:
        return deps_cache.get(dep_type, {}).get(role, []) or []

    # --------------------------------------------------------
    # Incoming edges: sources -> role
    # --------------------------------------------------------
    def incoming(role: str) -> Set[str]:
        return rev_cache.get(dep_type, {}).get(role, set())

    # --------------------------------------------------------
    # DFS traversal
    # --------------------------------------------------------
    def traverse(role: str, depth: int, path: Set[str]):
        ensure_node(role)

        if max_depth > 0 and depth >= max_depth:
            return

        if direction == "to":
            for tgt in outgoing(role):
                ensure_node(tgt)
                links.append({"source": role, "target": tgt, "type": dep_type})
                if tgt not in path:
                    traverse(tgt, depth + 1, path | {tgt})

        else:  # direction == "from"
            for src in incoming(role):
                ensure_node(src)
                links.append({"source": src, "target": role, "type": dep_type})
                if src not in path:
                    traverse(src, depth + 1, path | {src})

    traverse(start_role, 0, {start_role})

    return {"nodes": list(nodes.values()), "links": links}


# ------------------------------------------------------------
# Build all graph variants for one role
# ------------------------------------------------------------

def build_mappings(
    start_role: str,
    roles_dir: str,
    max_depth: int
) -> Dict[str, Any]:
    """
    Build all 12 graph variants (6 dep types × 2 directions).
    Accelerated version:
        - One-time scan of all metadata
        - One-time scan of all include_role/import_role
        - One-time scan of include_tasks/import_tasks
        - Build reverse-index tables
        - Then generate all graphs purely from memory
    """

    result: Dict[str, Any] = {}

    roles = [
        r for r in os.listdir(roles_dir)
        if os.path.isdir(os.path.join(roles_dir, r))
    ]

    # Pre-caches
    meta_cache: Dict[str, Dict[str, Any]] = {}
    deps_cache: Dict[str, Dict[str, List[str]]] = {dep: {} for dep in ALL_DEP_TYPES}
    rev_cache: Dict[str, Dict[str, Set[str]]] = {dep: {} for dep in ALL_DEP_TYPES}

    resolver = RoleDependencyResolver(roles_dir)

    # --------------------------------------------------------
    # Step 1: Preload meta-based deps (run_after, dependencies)
    # --------------------------------------------------------
    for role in roles:
        try:
            meta = load_meta(find_role_meta(roles_dir, role))
        except FileNotFoundError:
            continue

        meta_cache[role] = meta

        for dep_key in ["run_after", "dependencies"]:
            values = meta.get(dep_key, []) or []
            if isinstance(values, list) and values:
                deps_cache[dep_key][role] = values

                for tgt in values:
                    if isinstance(tgt, str) and tgt.strip():
                        rev_cache[dep_key].setdefault(tgt.strip(), set()).add(role)

    # --------------------------------------------------------
    # Step 2: Preload include_role/import_role (resolver)
    # --------------------------------------------------------
    for role in roles:
        role_path = os.path.join(roles_dir, role)
        inc, imp = resolver._scan_tasks(role_path)

        if inc:
            inc_list = sorted(inc)
            deps_cache["include_role"][role] = inc_list
            for tgt in inc_list:
                rev_cache["include_role"].setdefault(tgt, set()).add(role)

        if imp:
            imp_list = sorted(imp)
            deps_cache["import_role"][role] = imp_list
            for tgt in imp_list:
                rev_cache["import_role"].setdefault(tgt, set()).add(role)

    # --------------------------------------------------------
    # Step 3: Preload include_tasks/import_tasks
    # --------------------------------------------------------
    for role in roles:
        try:
            tasks_path = find_role_tasks(roles_dir, role)
        except FileNotFoundError:
            continue

        for dep_key in ["include_tasks", "import_tasks"]:
            values = load_tasks(tasks_path, dep_key)
            if values:
                deps_cache[dep_key][role] = values

                for tgt in values:
                    rev_cache[dep_key].setdefault(tgt, set()).add(role)

    caches = {
        "meta": meta_cache,
        "deps": deps_cache,
        "rev": rev_cache,
    }

    # --------------------------------------------------------
    # Step 4: Build all graphs from caches
    # --------------------------------------------------------
    for key in ALL_KEYS:
        dep_type, direction = key.rsplit("_", 1)
        try:
            result[key] = build_single_graph(
                start_role=start_role,
                dep_type=dep_type,
                direction=direction,
                roles_dir=roles_dir,
                max_depth=max_depth,
                caches=caches,
            )
        except Exception:
            result[key] = {"nodes": [], "links": []}

    return result


# ------------------------------------------------------------
# Output helper
# ------------------------------------------------------------

def output_graph(graph_data: Any, fmt: str, start: str, key: str):
    base = f"{start}_{key}"
    if fmt == "console":
        print(f"--- {base} ---")
        print(yaml.safe_dump(graph_data, sort_keys=False))

    else:
        path = f"{base}.{fmt}"
        with open(path, "w") as f:
            if fmt == "yaml":
                yaml.safe_dump(graph_data, f, sort_keys=False)
            else:
                json.dump(graph_data, f, indent=2)
        print(f"Wrote {path}")


# ------------------------------------------------------------
# CLI entrypoint
# ------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_roles_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "roles"))

    parser = argparse.ArgumentParser(description="Generate dependency graphs")
    parser.add_argument("-r", "--role", required=True, help="Starting role name")
    parser.add_argument("-D", "--depth", type=int, default=0, help="Max recursion depth")
    parser.add_argument("-o", "--output", choices=["yaml", "json", "console"], default="console")
    parser.add_argument("--roles-dir", default=default_roles_dir, help="Roles directory")

    args = parser.parse_args()

    graphs = build_mappings(args.role, args.roles_dir, args.depth)

    for key in ALL_KEYS:
        graph_data = graphs.get(key, {"nodes": [], "links": []})
        output_graph(graph_data, args.output, args.role, key)


if __name__ == "__main__":
    main()
