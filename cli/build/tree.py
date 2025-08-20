#!/usr/bin/env python3
import os
import argparse
import json
from typing import Dict, Any

from cli.build.graph import build_mappings, output_graph
from module_utils.role_dependency_resolver import RoleDependencyResolver


def find_roles(roles_dir: str):
    for entry in os.listdir(roles_dir):
        path = os.path.join(roles_dir, entry)
        if os.path.isdir(path):
            yield entry, path


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_roles_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "roles"))

    parser = argparse.ArgumentParser(
        description="Generate all graphs for each role and write meta/tree.json"
    )
    parser.add_argument("-d", "--role_dir", default=default_roles_dir,
                        help=f"Path to roles directory (default: {default_roles_dir})")
    parser.add_argument("-D", "--depth", type=int, default=0,
                        help="Max recursion depth (>0) or <=0 to stop on cycle")
    parser.add_argument("-o", "--output", choices=["yaml", "json", "console"],
                        default="json", help="Output format")
    parser.add_argument("-p", "--preview", action="store_true",
                        help="Preview graphs to console instead of writing files")
    parser.add_argument("-s", "--shadow-folder", type=str, default=None,
                        help="If set, writes tree.json to this shadow folder instead of the role's actual meta/ folder")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    # Toggles
    parser.add_argument("--no-include-role", action="store_true", help="Do not scan include_role")
    parser.add_argument("--no-import-role", action="store_true", help="Do not scan import_role")
    parser.add_argument("--no-dependencies", action="store_true", help="Do not read meta/main.yml dependencies")
    parser.add_argument("--no-run-after", action="store_true",
                        help="Do not read galaxy_info.run_after from meta/main.yml")

    args = parser.parse_args()

    if args.verbose:
        print(f"Roles directory: {args.role_dir}")
        print(f"Max depth: {args.depth}")
        print(f"Output format: {args.output}")
        print(f"Preview mode: {args.preview}")
        print(f"Shadow folder: {args.shadow_folder}")

    resolver = RoleDependencyResolver(args.role_dir)

    for role_name, role_path in find_roles(args.role_dir):
        if args.verbose:
            print(f"Processing role: {role_name}")

        graphs: Dict[str, Any] = build_mappings(
            start_role=role_name,
            roles_dir=args.role_dir,
            max_depth=args.depth
        )

        # Direct deps (depth=1) – getrennt erfasst für buckets
        inc_roles, imp_roles = resolver._scan_tasks(role_path)
        meta_deps = resolver._extract_meta_dependencies(role_path)
        run_after = set()
        if not args.no_run_after:
            run_after = resolver._extract_meta_run_after(role_path)

        if any([not args.no_include_role and inc_roles,
                not args.no_import_role and imp_roles,
                not args.no_dependencies and meta_deps,
                not args.no_run_after and run_after]):
            deps_root = graphs.setdefault("dependencies", {})
            if not args.no_include_role and inc_roles:
                deps_root["include_role"] = sorted(inc_roles)
            if not args.no_import_role and imp_roles:
                deps_root["import_role"] = sorted(imp_roles)
            if not args.no_dependencies and meta_deps:
                deps_root["dependencies"] = sorted(meta_deps)
            if not args.no_run_after and run_after:
                deps_root["run_after"] = sorted(run_after)
            graphs["dependencies"] = deps_root

        if args.preview:
            for key, data in graphs.items():
                if args.verbose:
                    print(f"Previewing graph '{key}' for role '{role_name}'")
                output_graph(data, "console", role_name, key)
        else:
            if args.shadow_folder:
                tree_file = os.path.join(args.shadow_folder, role_name, "meta", "tree.json")
            else:
                tree_file = os.path.join(role_path, "meta", "tree.json")
            os.makedirs(os.path.dirname(tree_file), exist_ok=True)
            with open(tree_file, "w", encoding="utf-8") as f:
                json.dump(graphs, f, indent=2)
            print(f"Wrote {tree_file}")


if __name__ == "__main__":
    main()
