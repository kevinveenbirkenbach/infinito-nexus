#!/usr/bin/env python3
"""Move unnecessary meta dependencies to guarded include_role/import_role.

A dependency is considered unnecessary when the consumer:

* does NOT use provider variables in defaults/vars/handlers (no
  early-var need), AND
* in tasks, any usage of provider vars or notifications of
  provider handlers happens only AFTER an include/import of the
  provider in the same file (or never).

Action per qualifying role:

* Remove the entry from ``roles/<role>/meta/main.yml``.
* Prepend a guarded include block to
  ``roles/<role>/tasks/01_core.yml`` (preferred) or
  ``roles/<role>/tasks/main.yml`` if the former is absent.
* When more than one dependency is moved, the include block uses a
  ``loop:``.

The heuristic mirrors
``tests/integration/test_unnecessary_role_dependencies.py``. YAML
round-trip preservation (comments, quotes, key order) is delegated
to ``ruamel.yaml`` via :mod:`.yaml_io`. Modified files get a
``.bak`` sibling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from utils.roles.mapping import ROLE_FILE_META_MAIN, ROLE_FILE_TASKS_MAIN

from .analysis import (
    collect_role_defined_vars,
    collect_role_handler_names,
    dependency_is_unnecessary,
    parse_meta_dependencies,
)
from .apply import (
    build_include_block_yaml,
    prepend_tasks,
    update_meta_remove_deps,
)
from .yaml_io import (
    iter_role_dirs,
    path_if_exists,
    role_name_from_dir,
    roles_root,
)


def build_providers_index(
    all_roles: list[str],
) -> dict[str, tuple[set[str], set[str]]]:
    return {
        role_name_from_dir(rd): (
            collect_role_defined_vars(rd),
            collect_role_handler_names(rd),
        )
        for rd in all_roles
    }


def process_role(
    role_dir: str,
    providers_index: dict[str, tuple[set[str], set[str]]],
    only_role: str | None,
    dry_run: bool,
) -> bool:
    consumer_name = role_name_from_dir(role_dir)
    if only_role and only_role != consumer_name:
        return False

    meta_deps = parse_meta_dependencies(role_dir)
    if not meta_deps:
        return False

    moved: list[str] = []
    for producer in meta_deps:
        if producer not in providers_index:
            continue
        pvars, phandlers = providers_index[producer]
        if dependency_is_unnecessary(
            role_dir, consumer_name, producer, pvars, phandlers
        ):
            moved.append(producer)

    if not moved:
        return False

    update_meta_remove_deps(
        str(Path(role_dir) / ROLE_FILE_META_MAIN), moved, dry_run=dry_run
    )

    target_tasks = path_if_exists(role_dir, "tasks/01_core.yml") or str(
        Path(role_dir) / ROLE_FILE_TASKS_MAIN
    )
    prepend_tasks(
        target_tasks,
        build_include_block_yaml(consumer_name, moved),
        dry_run=dry_run,
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Move unnecessary meta dependencies to guarded include_role for "
            "performance (preserve comments/quotes)."
        )
    )
    parser.add_argument(
        "--project-root",
        # nocheck: project-root-import  CLI default arg
        default=str(Path(__file__).resolve().parents[3]),
        help="Path to project root (default: two levels up from this script).",
    )
    parser.add_argument(
        "--role",
        dest="only_role",
        default=None,
        help="Only process a specific role name (e.g., 'docker-core').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and print planned changes without modifying files.",
    )
    args = parser.parse_args()

    roles = iter_role_dirs(args.project_root)
    if not roles:
        print(
            f"[ERR] No roles found under {roles_root(args.project_root)}",
            file=sys.stderr,
        )
        sys.exit(2)

    providers_index = build_providers_index(roles)

    changed_any = False
    for role_dir in roles:
        if process_role(role_dir, providers_index, args.only_role, args.dry_run):
            changed_any = True

    if not changed_any:
        print("[OK] No unnecessary meta dependencies to move (per heuristic).")
    elif args.dry_run:
        print("[DRY-RUN] Completed analysis. No files were changed.")
    else:
        print("[OK] Finished moving unnecessary dependencies.")


if __name__ == "__main__":
    main()
