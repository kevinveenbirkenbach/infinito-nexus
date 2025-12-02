#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create or update a full Ansible inventory for a single host and automatically
generate credentials for all selected applications.

This subcommand:

1. Uses `build inventory full` to generate a dynamic inventory for the given
   host containing all invokable applications.
2. Optionally filters the resulting groups by a user-provided list of
   application_ids (`--roles`).
3. Merges the generated inventory into an existing inventory file, without
   deleting or overwriting unrelated entries.
4. Ensures `host_vars/<host>.yml` exists and stores base settings such as:
   - PRIMARY_DOMAIN
   - WEB_PROTOCOL
   Existing keys are preserved (only missing keys are added).
5. For every application_id in the final inventory, uses:
   - `meta/applications/role_name.py` to resolve the role path
   - `create/credentials.py --snippet` to generate credentials YAML
     snippets, and merges all snippets into host_vars in a single write.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import concurrent.futures
import os 

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("Please `pip install pyyaml` to use `infinito create inventory`.")

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError:  # pragma: no cover
    raise SystemExit("Please `pip install ruamel.yaml` to use `infinito create inventory`.")


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def run_subprocess(
    cmd: List[str],
    capture_output: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command and either stream output or capture it.
    Raise SystemExit on non-zero return code.
    """
    if capture_output:
        result = subprocess.run(cmd, text=True, capture_output=True, env=env)
    else:
        result = subprocess.run(cmd, text=True, env=env)
    if result.returncode != 0:
        msg = f"Command failed: {' '.join(str(c) for c in cmd)}\n"
        if capture_output:
            msg += f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
        raise SystemExit(msg)
    return result

def build_env_with_project_root(project_root: Path) -> Dict[str, str]:
    """
    Return an environment dict where PYTHONPATH includes the project root.
    This makes `module_utils` and other top-level packages importable when
    running project scripts as subprocesses.
    """
    env = os.environ.copy()
    root_str = str(project_root)
    existing = env.get("PYTHONPATH")
    if existing:
        if root_str not in existing.split(os.pathsep):
            env["PYTHONPATH"] = root_str + os.pathsep + existing
    else:
        env["PYTHONPATH"] = root_str
    return env

def detect_project_root() -> Path:
    """
    Detect project root assuming this file is at: <root>/cli/create/inventory.py
    """
    here = Path(__file__).resolve()
    # .../repo/cli/create/inventory.py → parents[2] == repo
    return here.parents[2]


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Expected a mapping at top-level in {path}, got {type(data)}")
    return data


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def parse_roles_list(raw_roles: Optional[List[str]]) -> Optional[Set[str]]:
    """
    Parse a list of roles supplied on the CLI. Supports:
      --roles web-app-nextcloud web-app-mastodon
      --roles web-app-nextcloud,web-app-mastodon
    """
    if not raw_roles:
        return None
    result: Set[str] = set()
    for token in raw_roles:
        token = token.strip()
        if not token:
            continue
        # Allow comma-separated tokens as well
        for part in token.split(","):
            part = part.strip()
            if part:
                result.add(part)
    return result


# ---------------------------------------------------------------------------
# Inventory generation (servers.yml via build/inventory/full.py)
# ---------------------------------------------------------------------------

def generate_dynamic_inventory(
    host: str,
    roles_dir: Path,
    categories_file: Path,
    tmp_inventory: Path,
    project_root: Path,
) -> Dict[str, Any]:
    """
    Call `cli/build/inventory/full.py` directly to generate a dynamic inventory
    YAML for the given host and return it as a Python dict.
    """
    script = project_root / "cli" / "build" / "inventory" / "full.py"
    env = build_env_with_project_root(project_root)
    cmd = [
        sys.executable,
        str(script),
        "--host", host,
        "--format", "yaml",
        "--inventory-style", "group",
        "-c", str(categories_file),
        "-r", str(roles_dir),
        "-o", str(tmp_inventory),
    ]
    run_subprocess(cmd, capture_output=False, env=env)
    data = load_yaml(tmp_inventory)
    tmp_inventory.unlink(missing_ok=True)
    return data

def filter_inventory_by_roles(inv_data: Dict[str, Any], roles_filter: Set[str]) -> Dict[str, Any]:
    """
    Return a new inventory dict that contains only the groups whose names
    are in `roles_filter`. All other structure is preserved.
    """
    all_block = inv_data.get("all", {})
    children = all_block.get("children", {}) or {}

    filtered_children: Dict[str, Any] = {}
    for group_name, group_data in children.items():
        if group_name in roles_filter:
            filtered_children[group_name] = group_data

    new_all = dict(all_block)
    new_all["children"] = filtered_children
    return {"all": new_all}


def merge_inventories(
    base: Dict[str, Any],
    new: Dict[str, Any],
    host: str,
) -> Dict[str, Any]:
    """
    Merge `new` inventory into `base` inventory without deleting any
    existing groups/hosts/vars.

    For each group in `new`:
      - ensure the group exists in `base`
      - ensure `hosts` exists
      - ensure the given `host` is present in that group's `hosts`
        (keep existing hosts and host vars untouched)
    """
    base_all = base.setdefault("all", {})
    base_children = base_all.setdefault("children", {})

    new_all = new.get("all", {})
    new_children = new_all.get("children", {}) or {}

    for group_name, group_data in new_children.items():
        # Ensure group exists in base
        base_group = base_children.setdefault(group_name, {})
        base_hosts = base_group.setdefault("hosts", {})

        # Try to propagate host vars from new inventory if they exist
        new_hosts = (group_data or {}).get("hosts", {}) or {}
        host_vars = {}
        if isinstance(new_hosts, dict) and host in new_hosts:
            host_vars = new_hosts.get(host) or {}

        # Ensure the target host exists in this group
        if host not in base_hosts:
            base_hosts[host] = host_vars or {}

    return base

# ---------------------------------------------------------------------------
# host_vars helpers
# ---------------------------------------------------------------------------

def ensure_host_vars_file(
    host_vars_file: Path,
    host: str,
    primary_domain: str,
    web_protocol: str,
) -> None:
    """
    Ensure host_vars/<host>.yml exists and contains base settings.

    Important: Existing keys are NOT overwritten. Only missing keys are added:
      - PRIMARY_DOMAIN
      - WEB_PROTOCOL

    Uses ruamel.yaml so that custom tags like !vault are preserved and do not
    break parsing (unlike PyYAML safe_load).
    """
    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    if host_vars_file.exists():
        with host_vars_file.open("r", encoding="utf-8") as f:
            data = yaml_rt.load(f)
        if data is None:
            data = CommentedMap()
    else:
        data = CommentedMap()

    if not isinstance(data, CommentedMap):
        tmp = CommentedMap()
        for k, v in dict(data).items():
            tmp[k] = v
        data = tmp

    # Only set defaults; do NOT override existing values
    if "PRIMARY_DOMAIN" not in data:
        data["PRIMARY_DOMAIN"] = primary_domain
    if "WEB_PROTOCOL" not in data:
        data["WEB_PROTOCOL"] = web_protocol

    host_vars_file.parent.mkdir(parents=True, exist_ok=True)
    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(data, f)

def ensure_ruamel_map(node: CommentedMap, key: str) -> CommentedMap:
    """
    Ensure node[key] exists and is a mapping (CommentedMap).
    """
    if key not in node or not isinstance(node.get(key), CommentedMap):
        node[key] = CommentedMap()
    return node[key]


# ---------------------------------------------------------------------------
# Role resolution (meta/applications/role_name.py)
# ---------------------------------------------------------------------------

def resolve_role_path(
    application_id: str,
    roles_dir: Path,
    project_root: Path,
) -> Optional[Path]:
    """
    Use `cli/meta/applications/role_name.py` to resolve the role path
    for a given application_id. Returns an absolute Path or None on failure.

    We expect the helper to print either:
      - a bare role folder name (e.g. 'web-app-nextcloud'), or
      - a relative path like 'roles/web-app-nextcloud', or
      - an absolute path.

    We try, in order:
      1) <roles_dir>/<printed>
      2) <project_root>/<printed>
      3) use printed as-is if absolute
    """
    script = project_root / "cli" / "meta" / "applications" / "role_name.py"
    env = build_env_with_project_root(project_root)
    cmd = [
        sys.executable,
        str(script),
        application_id,
        "-r", str(roles_dir),
    ]
    result = run_subprocess(cmd, capture_output=True, env=env)
    raw = (result.stdout or "").strip()

    if not raw:
        print(f"[WARN] Could not resolve role for application_id '{application_id}'. Skipping.", file=sys.stderr)
        return None

    printed = Path(raw)

    # 1) If it's absolute, just use it
    if printed.is_absolute():
        role_path = printed
    else:
        # 2) Prefer resolving below roles_dir
        candidate = roles_dir / printed
        if candidate.exists():
            role_path = candidate
        else:
            # 3) Fallback: maybe the helper already printed something like 'roles/web-app-nextcloud'
            candidate2 = project_root / printed
            if candidate2.exists():
                role_path = candidate2
            else:
                print(
                    f"[WARN] Resolved role path does not exist after probing: "
                    f"{candidate} and {candidate2} (application_id={application_id})",
                    file=sys.stderr,
                )
                return None

    if not role_path.exists():
        print(f"[WARN] Resolved role path does not exist: {role_path} (application_id={application_id})", file=sys.stderr)
        return None

    return role_path

def fatal(msg: str) -> "NoReturn":
    """Print a fatal error and exit with code 1."""
    sys.stderr.write(f"[FATAL] {msg}\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Credentials generation via create/credentials.py --snippet
# ---------------------------------------------------------------------------

def _generate_credentials_snippet_for_app(
    app_id: str,
    roles_dir: Path,
    host_vars_file: Path,
    vault_password_file: Path,
    project_root: Path,
    credentials_script: Path,
) -> Optional[CommentedMap]:
    """
    Worker function for a single application_id:

      1. Resolve role path via meta/applications/role_name.py.
      2. Skip if role path cannot be resolved.
      3. Skip if schema/main.yml does not exist.
      4. Call create/credentials.py with --snippet to get a YAML fragment.

    Returns a ruamel CommentedMap (snippet) or None on failure.
    Errors are logged but do NOT abort the whole run.
    """
    try:
        role_path = resolve_role_path(app_id, roles_dir, project_root)
    except SystemExit as exc:
        sys.stderr.write(f"[ERROR] Failed to resolve role for {app_id}: {exc}\n")
        return None
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            f"[ERROR] Unexpected error while resolving role for {app_id}: {exc}\n"
        )
        return None

    if role_path is None:
        # resolve_role_path already logged a warning
        return None

    schema_path = role_path / "schema" / "main.yml"
    if not schema_path.exists():
        print(
            f"[INFO] Skipping {app_id}: no schema/main.yml found at {schema_path}",
            file=sys.stderr,
        )
        return None

    cmd = [
        sys.executable,
        str(credentials_script),
        "--role-path", str(role_path),
        "--inventory-file", str(host_vars_file),
        "--vault-password-file", str(vault_password_file),
        "--snippet",
        "--allow-empty-plain",
    ]
    print(f"[INFO] Generating credentials snippet for {app_id} (role: {role_path})")

    env = build_env_with_project_root(project_root)
    result = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if result.returncode != 0:
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        fatal(
            f"Command failed ({result.returncode}): {' '.join(map(str, cmd))}\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )

    snippet_text = (result.stdout or "").strip()
    if not snippet_text:
        # No output means nothing to merge
        return None

    yaml_rt = YAML(typ="rt")
    try:
        data = yaml_rt.load(snippet_text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            f"[ERROR] Failed to parse credentials snippet for {app_id}: {exc}\n"
            f"Snippet was:\n{snippet_text}\n"
        )
        return None

    if data is None:
        return None
    if not isinstance(data, CommentedMap):
        # Normalize to CommentedMap
        cm = CommentedMap()
        for k, v in dict(data).items():
            cm[k] = v
        return cm

    return data


def generate_credentials_for_roles(
    application_ids: List[str],
    roles_dir: Path,
    host_vars_file: Path,
    vault_password_file: Path,
    project_root: Path,
    workers: int = 4,
) -> None:
    """
    Generate credentials for all given application_ids using create/credentials.py --snippet.

    Steps:
      1) In parallel, for each app_id:
         - resolve role path
         - skip roles without schema/main.yml
         - run create/credentials.py --snippet
         - return a YAML snippet (ruamel CommentedMap)
      2) Sequentially, merge all snippets into host_vars/<host>.yml in a single write:
         - applications.<app_id>.credentials.<key> is added only if missing
         - ansible_become_password is added only if missing
    """
    if not application_ids:
        print("[WARN] No application_ids to process for credential generation.", file=sys.stderr)
        return

    credentials_script = project_root / "cli" / "create" / "credentials.py"
    max_workers = max(1, workers)
    print(
        f"[INFO] Running credentials snippet generation for {len(application_ids)} "
        f"applications with {max_workers} worker threads..."
    )

    snippets: List[CommentedMap] = []

    # 1) Parallel: collect snippets
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_app: Dict[concurrent.futures.Future, str] = {}

        for app_id in application_ids:
            future = executor.submit(
                _generate_credentials_snippet_for_app,
                app_id,
                roles_dir,
                host_vars_file,
                vault_password_file,
                project_root,
                credentials_script,
            )
            future_to_app[future] = app_id

        for future in concurrent.futures.as_completed(future_to_app):
            app_id = future_to_app[future]
            try:
                snippet = future.result()
            except Exception as exc:
                fatal(f"Worker for {app_id} failed with exception: {exc}")

            if snippet is not None:
                snippets.append(snippet)

    if not snippets:
        print("[WARN] No credentials snippets were generated.", file=sys.stderr)
        return

    # 2) Sequential: merge snippets into host_vars
    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    if host_vars_file.exists():
        with host_vars_file.open("r", encoding="utf-8") as f:
            doc = yaml_rt.load(f)
        if doc is None:
            doc = CommentedMap()
    else:
        doc = CommentedMap()

    if not isinstance(doc, CommentedMap):
        tmp = CommentedMap()
        for k, v in dict(doc).items():
            tmp[k] = v
        doc = tmp

    # Merge each snippet
    for snippet in snippets:
        apps_snip = snippet.get("applications", {}) or {}
        if isinstance(apps_snip, dict):
            apps_doc = ensure_ruamel_map(doc, "applications")
            for app_id, app_block_snip in apps_snip.items():
                if not isinstance(app_block_snip, dict):
                    continue
                app_doc = ensure_ruamel_map(apps_doc, app_id)
                creds_doc = ensure_ruamel_map(app_doc, "credentials")

                creds_snip = app_block_snip.get("credentials", {}) or {}
                if not isinstance(creds_snip, dict):
                    continue

                for key, val in creds_snip.items():
                    # Only add missing keys; do not overwrite existing credentials
                    if key not in creds_doc:
                        creds_doc[key] = val

        # ansible_become_password: only add if missing
        if "ansible_become_password" in snippet and "ansible_become_password" not in doc:
            doc["ansible_become_password"] = snippet["ansible_become_password"]

    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create or update a full inventory for a host and generate "
            "credentials for all selected applications."
        )
    )
    parser.add_argument(
        "--host",
        required=True,
        help="Hostname to use in the inventory (e.g. galaxyserver, localhost).",
    )
    parser.add_argument(
        "--primary-domain",
        required=True,
        help="Primary domain for this host (e.g. infinito.nexus).",
    )
    parser.add_argument(
        "--web-protocol",
        default="https",
        choices=("http", "https"),
        help="Web protocol to use for this host (default: https).",
    )
    parser.add_argument(
        "--inventory-dir",
        required=True,
        help="Path to the inventory directory (e.g. inventories/galaxyserver).",
    )
    parser.add_argument(
        "--inventory-file",
        help="Inventory YAML file path (default: <inventory-dir>/servers.yml).",
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        help=(
            "Optional list of application_ids to include. "
            "If omitted, all invokable applications are used. "
            "Supports comma-separated values as well."
        ),
    )
    parser.add_argument(
        "--vault-password-file",
        required=True,
        help="Path to the Vault password file for credentials generation.",
    )
    parser.add_argument(
        "--roles-dir",
        help="Path to the roles/ directory (default: <project-root>/roles).",
    )
    parser.add_argument(
        "--categories-file",
        help="Path to roles/categories.yml (default: <roles-dir>/categories.yml).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads for parallel credentials snippet generation (default: 4).",
    )

    args = parser.parse_args(argv)

    project_root = detect_project_root()
    roles_dir = Path(args.roles_dir) if args.roles_dir else (project_root / "roles")
    categories_file = Path(args.categories_file) if args.categories_file else (roles_dir / "categories.yml")

    inventory_dir = Path(args.inventory_dir).resolve()
    inventory_dir.mkdir(parents=True, exist_ok=True)

    inventory_file = Path(args.inventory_file) if args.inventory_file else (inventory_dir / "servers.yml")
    inventory_file = inventory_file.resolve()

    host_vars_dir = inventory_dir / "host_vars"
    host_vars_file = host_vars_dir / f"{args.host}.yml"

    vault_password_file = Path(args.vault_password_file).resolve()

    roles_filter = parse_roles_list(args.roles)
    tmp_inventory = inventory_dir / "_inventory_full_tmp.yml"

    # 1) Generate dynamic inventory via build/inventory/full.py
    print("[INFO] Generating dynamic inventory via cli/build/inventory/full.py ...")
    dyn_inv = generate_dynamic_inventory(
        host=args.host,
        roles_dir=roles_dir,
        categories_file=categories_file,
        tmp_inventory=tmp_inventory,
        project_root=project_root,
    )

    # 2) Optional: filter by roles
    if roles_filter:
        print(f"[INFO] Filtering inventory to roles: {', '.join(sorted(roles_filter))}")
        dyn_inv = filter_inventory_by_roles(dyn_inv, roles_filter)

    # Collect final application_ids from dynamic inventory for credential generation
    dyn_all = dyn_inv.get("all", {})
    dyn_children = dyn_all.get("children", {}) or {}
    application_ids = sorted(dyn_children.keys())

    if not application_ids:
        print("[WARN] No application_ids found in dynamic inventory after filtering. Nothing to do.", file=sys.stderr)

    # 3) Merge with existing inventory file (if any)
    if inventory_file.exists():
        print(f"[INFO] Merging into existing inventory: {inventory_file}")
        base_inv = load_yaml(inventory_file)
    else:
        print(f"[INFO] Creating new inventory file: {inventory_file}")
        base_inv = {}

    merged_inv = merge_inventories(base_inv, dyn_inv, host=args.host)
    dump_yaml(inventory_file, merged_inv)

    # 4) Ensure host_vars/<host>.yml exists and has base settings
    print(f"[INFO] Ensuring host_vars for host '{args.host}' at {host_vars_file}")
    ensure_host_vars_file(
        host_vars_file=host_vars_file,
        host=args.host,
        primary_domain=args.primary_domain,
        web_protocol=args.web_protocol,
    )

    # 5) Generate credentials for all application_ids (snippets + single merge)
    if application_ids:
        print(f"[INFO] Generating credentials for {len(application_ids)} applications...")
        generate_credentials_for_roles(
            application_ids=application_ids,
            roles_dir=roles_dir,
            host_vars_file=host_vars_file,
            vault_password_file=vault_password_file,
            project_root=project_root,
            workers=args.workers,
        )

    print("[INFO] Done. Inventory and host_vars updated without deleting existing values.")


if __name__ == "__main__":  # pragma: no cover
    main()
