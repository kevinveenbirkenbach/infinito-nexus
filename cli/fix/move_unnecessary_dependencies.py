#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Move unnecessary meta dependencies to guarded include_role/import_role
for better performance, while preserving YAML comments, quotes, and layout.

Heuristic (matches tests/integration/test_unnecessary_role_dependencies.py):
- A dependency is considered UNNECESSARY if:
  * The consumer does NOT use provider variables in defaults/vars/handlers
    (no early-var need), AND
  * In tasks, any usage of provider vars or provider-handler notifications
    occurs only AFTER an include/import of the provider in the same file,
    OR there is no usage at all.

Action:
- Remove such dependencies from roles/<role>/meta/main.yml.
- Prepend a guarded include block to roles/<role>/tasks/01_core.yml (preferred)
  or roles/<role>/tasks/main.yml if 01_core.yml is absent.
- If multiple dependencies are moved for a role, use a loop over include_role.

Notes:
- Creates .bak backups for modified YAML files.
- Requires ruamel.yaml to preserve comments/quotes everywhere.
"""

import argparse
import glob
import os
import re
import shutil
import sys
from typing import Dict, Set, List, Tuple, Optional

# --- Require ruamel.yaml for full round-trip preservation ---
try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    from ruamel.yaml.scalarstring import SingleQuotedScalarString
    _HAVE_RUAMEL = True
except Exception:
    _HAVE_RUAMEL = False

if not _HAVE_RUAMEL:
    print("[ERR] ruamel.yaml is required to preserve comments/quotes. Install with: pip install ruamel.yaml", file=sys.stderr)
    sys.exit(3)

yaml_rt = YAML()
yaml_rt.preserve_quotes = True
yaml_rt.width = 10**9  # prevent line wrapping

# ---------------- Utilities ----------------

def _backup(path: str):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def load_yaml_rt(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml_rt.load(f)
        return data if data is not None else CommentedMap()
    except FileNotFoundError:
        return CommentedMap()
    except Exception as e:
        print(f"[WARN] Failed to parse YAML: {path}: {e}", file=sys.stderr)
        return CommentedMap()

def dump_yaml_rt(data, path: str):
    _backup(path)
    with open(path, "w", encoding="utf-8") as f:
        yaml_rt.dump(data, f)

def roles_root(project_root: str) -> str:
    return os.path.join(project_root, "roles")

def iter_role_dirs(project_root: str) -> List[str]:
    root = roles_root(project_root)
    return [d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)]

def role_name_from_dir(role_dir: str) -> str:
    return os.path.basename(role_dir.rstrip(os.sep))

def path_if_exists(*parts) -> Optional[str]:
    p = os.path.join(*parts)
    return p if os.path.exists(p) else None

def gather_yaml_files(base: str, patterns: List[str]) -> List[str]:
    files: List[str] = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(base, pat), recursive=True))
    return [f for f in files if os.path.isfile(f)]

def sq(v: str):
    """Return a single-quoted scalar (ruamel) for consistent quoting."""
    return SingleQuotedScalarString(v)

# ---------------- Providers: vars & handlers ----------------

def flatten_keys(data) -> Set[str]:
    out: Set[str] = set()
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(k, str):
                out.add(k)
            out |= flatten_keys(v)
    elif isinstance(data, list):
        for item in data:
            out |= flatten_keys(item)
    return out

def collect_role_defined_vars(role_dir: str) -> Set[str]:
    """Vars a role 'provides': defaults/vars keys + set_fact keys in tasks."""
    provided: Set[str] = set()

    for rel in ("defaults/main.yml", "vars/main.yml"):
        p = path_if_exists(role_dir, rel)
        if p:
            data = load_yaml_rt(p)
            provided |= flatten_keys(data)

    # set_fact keys
    task_files = gather_yaml_files(os.path.join(role_dir, "tasks"), ["**/*.yml", "*.yml"])
    for tf in task_files:
        data = load_yaml_rt(tf)
        if isinstance(data, list):
            for task in data:
                if isinstance(task, dict) and "set_fact" in task and isinstance(task["set_fact"], dict):
                    provided |= set(task["set_fact"].keys())

    noisy = {"when", "name", "vars", "tags", "register"}
    return {v for v in provided if isinstance(v, str) and v and v not in noisy}

def collect_role_handler_names(role_dir: str) -> Set[str]:
    """Handler names defined by a role (for notify detection)."""
    handler_file = path_if_exists(role_dir, "handlers/main.yml")
    if not handler_file:
        return set()
    data = load_yaml_rt(handler_file)
    names: Set[str] = set()
    if isinstance(data, list):
        for task in data:
            if isinstance(task, dict):
                nm = task.get("name")
                if isinstance(nm, str) and nm.strip():
                    names.add(nm.strip())
    return names

# ---------------- Consumers: usage scanning ----------------

def find_var_positions(text: str, varname: str) -> List[int]:
    """Return byte offsets for occurrences of varname (word-ish boundary)."""
    positions: List[int] = []
    if not varname:
        return positions
    pattern = re.compile(rf"(?<!\w){re.escape(varname)}(?!\w)")
    for m in pattern.finditer(text):
        positions.append(m.start())
    return positions

def first_var_use_offset_in_text(text: str, provided_vars: Set[str]) -> Optional[int]:
    first: Optional[int] = None
    for v in provided_vars:
        for off in find_var_positions(text, v):
            if first is None or off < first:
                first = off
    return first

def first_include_offset_for_role(text: str, producer_role: str) -> Optional[int]:
    """
    Find earliest include/import of a given role in this YAML text.
    Handles compact dict and block styles.
    """
    pattern = re.compile(
        r"(include_role|import_role)\s*:\s*\{[^}]*\bname\s*:\s*['\"]?"
        + re.escape(producer_role) + r"['\"]?[^}]*\}"
        r"|"
        r"(include_role|import_role)\s*:\s*\n(?:\s+[a-z_]+\s*:\s*.*\n)*\s*name\s*:\s*['\"]?"
        + re.escape(producer_role) + r"['\"]?",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    return m.start() if m else None

def find_notify_offsets_for_handlers(text: str, handler_names: Set[str]) -> List[int]:
    """
    Heuristic: for each handler name, find occurrences where 'notify' appears within
    the preceding ~200 chars. Works for single string or list-style notify blocks.
    """
    if not handler_names:
        return []
    offsets: List[int] = []
    for h in handler_names:
        for m in re.finditer(re.escape(h), text):
            start = m.start()
            back = max(0, start - 200)
            context = text[back:start]
            if re.search(r"notify\s*:", context):
                offsets.append(start)
    return sorted(offsets)

def parse_meta_dependencies(role_dir: str) -> List[str]:
    meta = path_if_exists(role_dir, "meta/main.yml")
    if not meta:
        return []
    data = load_yaml_rt(meta)
    dd = data.get("dependencies")
    deps: List[str] = []
    if isinstance(dd, list):
        for item in dd:
            if isinstance(item, str):
                deps.append(item)
            elif isinstance(item, dict) and "role" in item:
                deps.append(str(item["role"]))
            elif isinstance(item, dict) and "name" in item:
                deps.append(str(item["name"]))
    return deps

# ---------------- Fix application ----------------

def sanitize_run_once_var(role_name: str) -> str:
    """
    Generate run_once variable name from role name.
    Example: 'srv-web-7-7-inj-logout' -> 'run_once_srv_web_7_7_inj_logout'
    """
    return "run_once_" + role_name.replace("-", "_")

def build_include_block_yaml(consumer_role: str, moved_deps: List[str]) -> List[dict]:
    """
    Build a guarded block that includes one or many roles.
    This block will be prepended to tasks/01_core.yml or tasks/main.yml.
    """
    guard_var = sanitize_run_once_var(consumer_role)

    if len(moved_deps) == 1:
        inner_tasks = [
            {
                "name": f"Include dependency '{moved_deps[0]}'",
                "include_role": {"name": moved_deps[0]},
            }
        ]
    else:
        inner_tasks = [
            {
                "name": "Include dependencies",
                "include_role": {"name": "{{ item }}"},
                "loop": moved_deps,
            }
        ]

    # Always set the run_once fact at the end
    inner_tasks.append({"set_fact": {guard_var: True}})

    # Correct Ansible block structure
    block_task = {
        "name": "Load former meta dependencies once",
        "block": inner_tasks,
        "when": f"{guard_var} is not defined",
    }

    return [block_task]

def prepend_tasks(tasks_path: str, new_tasks, dry_run: bool):
    """
    Prepend new_tasks (CommentedSeq) to an existing tasks YAML list while preserving comments.
    If the file does not exist, create it with new_tasks.
    """
    if os.path.exists(tasks_path):
        existing = load_yaml_rt(tasks_path)
        if isinstance(existing, list):
            combined = CommentedSeq()
            for item in new_tasks:
                combined.append(item)
            for item in existing:
                combined.append(item)
        elif isinstance(existing, dict):
            # Rare case: tasks file with a single mapping; coerce to list
            combined = CommentedSeq()
            for item in new_tasks:
                combined.append(item)
            combined.append(existing)
        else:
            combined = new_tasks
    else:
        os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
        combined = new_tasks

    if dry_run:
        print(f"[DRY-RUN] Would write {tasks_path} with {len(new_tasks)} prepended task(s).")
        return

    dump_yaml_rt(combined, tasks_path)
    print(f"[OK] Updated {tasks_path} (prepended {len(new_tasks)} task(s)).")

def update_meta_remove_deps(meta_path: str, remove: List[str], dry_run: bool):
    """
    Remove entries from meta.dependencies while leaving the rest of the file intact.
    Quotes, comments, key order, and line breaks are preserved.
    Returns True if a change would be made (or was made when not in dry-run).
    """
    if not os.path.exists(meta_path):
        return False

    doc = load_yaml_rt(meta_path)
    deps = doc.get("dependencies")
    if not isinstance(deps, list):
        return False

    def dep_name(item):
        if isinstance(item, dict):
            return item.get("role") or item.get("name")
        return item

    keep = CommentedSeq()
    removed = []
    for item in deps:
        name = dep_name(item)
        if name in remove:
            removed.append(name)
        else:
            keep.append(item)

    if not removed:
        return False

    if keep:
        doc["dependencies"] = keep
    else:
        if "dependencies" in doc:
            del doc["dependencies"]

    if dry_run:
        print(f"[DRY-RUN] Would rewrite {meta_path}; removed: {', '.join(removed)}")
        return True

    dump_yaml_rt(doc, meta_path)
    print(f"[OK] Rewrote {meta_path}; removed: {', '.join(removed)}")
    return True

def dependency_is_unnecessary(consumer_dir: str,
                              consumer_name: str,
                              producer_name: str,
                              provider_vars: Set[str],
                              provider_handlers: Set[str]) -> bool:
    """Apply heuristic to decide if we can move this dependency."""
    # 1) Early usage in defaults/vars/handlers? If yes -> necessary
    defaults_files = [p for p in [
        path_if_exists(consumer_dir, "defaults/main.yml"),
        path_if_exists(consumer_dir, "vars/main.yml"),
        path_if_exists(consumer_dir, "handlers/main.yml"),
    ] if p]
    for p in defaults_files:
        text = read_text(p)
        if first_var_use_offset_in_text(text, provider_vars) is not None:
            return False  # needs meta dep

    # 2) Tasks: any usage before include/import? If yes -> keep meta dep
    task_files = gather_yaml_files(os.path.join(consumer_dir, "tasks"), ["**/*.yml", "*.yml"])
    for p in task_files:
        text = read_text(p)
        if not text:
            continue
        include_off = first_include_offset_for_role(text, producer_name)
        var_use_off = first_var_use_offset_in_text(text, provider_vars)
        notify_offs = find_notify_offsets_for_handlers(text, provider_handlers)

        if var_use_off is not None:
            if include_off is None or include_off > var_use_off:
                return False  # used before include

        for noff in notify_offs:
            if include_off is None or include_off > noff:
                return False  # notify before include

    # If we get here: no early use, and either no usage at all or usage after include
    return True

def process_role(role_dir: str,
                 providers_index: Dict[str, Tuple[Set[str], Set[str]]],
                 only_role: Optional[str],
                 dry_run: bool) -> bool:
    """
    Returns True if any change suggested/made for this role.
    """
    consumer_name = role_name_from_dir(role_dir)
    if only_role and only_role != consumer_name:
        return False

    meta_deps = parse_meta_dependencies(role_dir)
    if not meta_deps:
        return False

    # Build provider vars/handlers accessors
    moved: List[str] = []
    for producer in meta_deps:
        # Only consider local roles we can analyze
        producer_dir = path_if_exists(os.path.dirname(role_dir), producer) or path_if_exists(os.path.dirname(roles_root(os.path.dirname(role_dir))), "roles", producer)
        if producer not in providers_index:
            # Unknown/external role → skip (we cannot verify safety)
            continue
        pvars, phandlers = providers_index[producer]
        if dependency_is_unnecessary(role_dir, consumer_name, producer, pvars, phandlers):
            moved.append(producer)

    if not moved:
        return False

    # 1) Remove from meta
    meta_path = os.path.join(role_dir, "meta", "main.yml")
    update_meta_remove_deps(meta_path, moved, dry_run=dry_run)

    # 2) Prepend include block to tasks/01_core.yml or tasks/main.yml
    target_tasks = path_if_exists(role_dir, "tasks/01_core.yml")
    if not target_tasks:
        target_tasks = os.path.join(role_dir, "tasks", "main.yml")
    include_block = build_include_block_yaml(consumer_name, moved)
    prepend_tasks(target_tasks, include_block, dry_run=dry_run)
    return True

def build_providers_index(all_roles: List[str]) -> Dict[str, Tuple[Set[str], Set[str]]]:
    """
    Map role_name -> (provided_vars, handler_names)
    """
    index: Dict[str, Tuple[Set[str], Set[str]]] = {}
    for rd in all_roles:
        rn = role_name_from_dir(rd)
        index[rn] = (collect_role_defined_vars(rd), collect_role_handler_names(rd))
    return index

def main():
    parser = argparse.ArgumentParser(
        description="Move unnecessary meta dependencies to guarded include_role for performance (preserve comments/quotes)."
    )
    parser.add_argument(
        "--project-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
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
        print(f"[ERR] No roles found under {roles_root(args.project_root)}", file=sys.stderr)
        sys.exit(2)

    providers_index = build_providers_index(roles)

    changed_any = False
    for role_dir in roles:
        changed = process_role(role_dir, providers_index, args.only_role, args.dry_run)
        changed_any = changed_any or changed

    if not changed_any:
        print("[OK] No unnecessary meta dependencies to move (per heuristic).")
    else:
        if args.dry_run:
            print("[DRY-RUN] Completed analysis. No files were changed.")
        else:
            print("[OK] Finished moving unnecessary dependencies.")

if __name__ == "__main__":
    main()
