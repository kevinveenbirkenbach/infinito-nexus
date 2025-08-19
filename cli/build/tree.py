#!/usr/bin/env python3
import os
import argparse
import json
import fnmatch
import re
from typing import Dict, Any

import yaml

from cli.build.graph import build_mappings, output_graph


def find_roles(roles_dir: str):
    """Yield (role_name, role_path) for every subfolder in roles_dir."""
    for entry in os.listdir(roles_dir):
        path = os.path.join(roles_dir, entry)
        if os.path.isdir(path):
            yield entry, path


def _is_pure_jinja_var(s: str) -> bool:
    """Check if string is exactly a single {{ var }} expression."""
    return bool(re.fullmatch(r"\s*\{\{\s*[^}]+\s*\}\}\s*", s))


def _jinja_to_glob(s: str) -> str:
    """Convert Jinja placeholders {{ ... }} into * for fnmatch."""
    pattern = re.sub(r"\{\{[^}]+\}\}", "*", s)
    pattern = re.sub(r"\*{2,}", "*", pattern)
    return pattern.strip()


def _list_role_dirs(roles_dir: str) -> list[str]:
    """Return a list of role directory names inside roles_dir."""
    return [
        d for d in os.listdir(roles_dir)
        if os.path.isdir(os.path.join(roles_dir, d))
    ]


def find_include_role_dependencies(role_path: str, roles_dir: str) -> set[str]:
    """
    Scan all tasks/*.yml(.yaml) files of a role and collect include_role dependencies.

    Rules:
      - loop/with_items with literal strings -> add those as roles
      - name contains jinja AND surrounding literals -> convert to glob and match existing roles
      - name is a pure jinja variable only -> ignore
      - name is a pure literal -> add as-is
    """
    deps: set[str] = set()
    tasks_dir = os.path.join(role_path, "tasks")
    if not os.path.isdir(tasks_dir):
        return deps

    candidates = []
    for root, _, files in os.walk(tasks_dir):
        for f in files:
            if f.endswith(".yml") or f.endswith(".yaml"):
                candidates.append(os.path.join(root, f))

    all_roles = _list_role_dirs(roles_dir)

    def add_literal_loop_items(loop_val):
        if isinstance(loop_val, list):
            for item in loop_val:
                if isinstance(item, str) and item.strip():
                    deps.add(item.strip())

    for file_path in candidates:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
        except Exception:
            # Be tolerant to any parsing issues; skip unreadable files
            continue

        for doc in docs:
            if not isinstance(doc, list):
                continue
            for task in doc:
                if not isinstance(task, dict):
                    continue
                if "include_role" not in task:
                    continue
                inc = task.get("include_role")
                if not isinstance(inc, dict):
                    continue
                name = inc.get("name")
                if not isinstance(name, str) or not name.strip():
                    continue

                # 1) Handle loop/with_items
                loop_val = task.get("loop", task.get("with_items"))
                if loop_val is not None:
                    add_literal_loop_items(loop_val)
                    # still check name for surrounding literals
                    if not _is_pure_jinja_var(name):
                        pattern = (
                            _jinja_to_glob(name)
                            if ("{{" in name and "}}" in name)
                            else name
                        )
                        if "*" in pattern:
                            for r in all_roles:
                                if fnmatch.fnmatch(r, pattern):
                                    deps.add(r)
                    continue

                # 2) No loop: evaluate name
                if "{{" in name and "}}" in name:
                    if _is_pure_jinja_var(name):
                        continue  # ignore pure variable
                    pattern = _jinja_to_glob(name)
                    if "*" in pattern:
                        for r in all_roles:
                            if fnmatch.fnmatch(r, pattern):
                                deps.add(r)
                        continue
                    else:
                        deps.add(pattern)
                else:
                    # pure literal
                    deps.add(name.strip())

    return deps


def main():
    # default roles dir is ../../roles relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_roles_dir = os.path.abspath(
        os.path.join(script_dir, "..", "..", "roles")
    )

    parser = argparse.ArgumentParser(
        description="Generate all graphs for each role and write meta/tree.json"
    )
    parser.add_argument(
        "-d", "--role_dir",
        default=default_roles_dir,
        help=f"Path to roles directory (default: {default_roles_dir})"
    )
    parser.add_argument(
        "-D", "--depth",
        type=int,
        default=0,
        help="Max recursion depth (>0) or <=0 to stop on cycle"
    )
    parser.add_argument(
        "-o", "--output",
        choices=["yaml", "json", "console"],
        default="json",
        help="Output format"
    )
    parser.add_argument(
        "-p", "--preview",
        action="store_true",
        help="Preview graphs to console instead of writing files"
    )
    parser.add_argument(
        "-s", "--shadow-folder",
        type=str,
        default=None,
        help="If set, writes tree.json to this shadow folder instead of the role's actual meta/ folder"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()

    if args.verbose:
        print(f"Roles directory: {args.role_dir}")
        print(f"Max depth: {args.depth}")
        print(f"Output format: {args.output}")
        print(f"Preview mode: {args.preview}")
        print(f"Shadow folder: {args.shadow_folder}")

    for role_name, role_path in find_roles(args.role_dir):
        if args.verbose:
            print(f"Processing role: {role_name}")

        graphs: Dict[str, Any] = build_mappings(
            start_role=role_name,
            roles_dir=args.role_dir,
            max_depth=args.depth
        )

        # add include_role dependencies from tasks
        include_deps = find_include_role_dependencies(role_path, args.role_dir)
        if include_deps:
            deps_root = graphs.setdefault("dependencies", {})
            inc_list = set(deps_root.get("include_role", []))
            inc_list.update(include_deps)
            deps_root["include_role"] = sorted(inc_list)
            graphs["dependencies"] = deps_root

        if args.preview:
            for key, data in graphs.items():
                if args.verbose:
                    print(f"Previewing graph '{key}' for role '{role_name}'")
                output_graph(data, "console", role_name, key)
        else:
            if args.shadow_folder:
                tree_file = os.path.join(
                    args.shadow_folder, role_name, "meta", "tree.json"
                )
            else:
                tree_file = os.path.join(role_path, "meta", "tree.json")
            os.makedirs(os.path.dirname(tree_file), exist_ok=True)
            with open(tree_file, "w") as f:
                json.dump(graphs, f, indent=2)
            print(f"Wrote {tree_file}")


if __name__ == "__main__":
    main()
