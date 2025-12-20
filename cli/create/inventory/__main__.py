#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create or update a full Ansible inventory for a single host and automatically
generate credentials for all selected applications.

This subcommand:

1. Uses `build inventory full` to generate a dynamic inventory for the given
   host containing all invokable applications.
2. Optionally filters the resulting groups by:
   - --include: only listed application_ids are kept
   - --exclude:  listed application_ids are removed
   - --roles:   legacy include filter (used only if --include/--exclude are not set)
3. Merges the generated inventory into an existing inventory file, without
   deleting or overwriting unrelated entries.
4. Ensures `host_vars/<host>.yml` exists and stores base settings such as:
   - PRIMARY_DOMAIN (optional)
   - SSL_ENABLED
   - networks.internet.ip4
   - networks.internet.ip6
   Existing keys are preserved (only missing keys are added).
5. For every application_id in the final inventory, uses:
   - `meta/applications/role_name.py` to resolve the role path
   - `create/credentials.py --snippet` to generate credentials YAML
     snippets, and merges all snippets into host_vars in a single write.
6. If --vault-password-file is not provided, a file `.password` is created
   in the inventory directory (if missing) and used as vault password file.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, NoReturn
import concurrent.futures
import os
import secrets
import string
import json

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("Please `pip install pyyaml` to use `infinito create inventory`.")

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Please `pip install ruamel.yaml` to use `infinito create inventory`."
    )

from module_utils.handler.vault import VaultHandler

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


def deep_update_commented_map(target: CommentedMap, updates: Dict[str, Any]) -> None:
    """
    Recursively merge updates into a ruamel CommentedMap.

    - If a value in updates is a mapping, it is merged into the existing mapping.
    - Non-mapping values overwrite existing values.
    """
    for key, value in updates.items():
        if isinstance(value, dict):
            existing = target.get(key)
            if not isinstance(existing, CommentedMap):
                existing = CommentedMap()
                target[key] = existing
            deep_update_commented_map(existing, value)
        else:
            target[key] = value


def apply_vars_overrides(host_vars_file: Path, json_str: str) -> None:
    """
    Apply JSON overrides to host_vars/<host>.yml.

    Behavior:
      - json_str must contain a JSON object at the top level.
      - All keys in that object (possibly nested) are merged into the
        existing document.
      - Existing values are overwritten by values from the JSON.
      - Non-existing keys are created.

    Example:
        --vars '{"SSL_ENABLED": false, "networks": {"internet": {"ip4": "10.0.0.10"}}}'
    """
    try:
        overrides = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON passed to --vars: {exc}") from exc

    if not isinstance(overrides, dict):
        raise SystemExit("JSON for --vars must be an object at the top level.")

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

    deep_update_commented_map(doc, overrides)

    host_vars_file.parent.mkdir(parents=True, exist_ok=True)
    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)


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


def ensure_become_password(
    host_vars_file: Path,
    vault_password_file: Path,
    become_password: Optional[str],
) -> None:
    """
    Ensure ansible_become_password exists and is stored as a vaulted string
    according to the following rules:

      - If become_password is provided:
          Encrypt it with Ansible Vault and set/overwrite ansible_become_password.
      - If become_password is not provided and ansible_become_password already exists:
          Do nothing (respect the existing value, even if it is plain text).
      - If become_password is not provided and ansible_become_password is missing:
          Generate a random password, encrypt it, and set ansible_become_password.

    The encryption is done via module_utils.handler.vault.VaultHandler so that the
    resulting value is a !vault tagged scalar in host_vars.
    """
    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    # Load existing host_vars document (created earlier by ensure_host_vars_file)
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

    current_value = doc.get("ansible_become_password")

    # Case 1: no explicit password provided, but value already exists → respect it
    if become_password is None and current_value is not None:
        return

    # Case 2: explicit password provided → use it
    # Case 3: no password provided and no value present → generate a random one
    if become_password is not None:
        plain_password = become_password
    else:
        plain_password = generate_random_password()

    # Use VaultHandler to encrypt the password via ansible-vault encrypt_string
    handler = VaultHandler(str(vault_password_file))
    snippet_text = handler.encrypt_string(plain_password, "ansible_become_password")

    # Parse the snippet with ruamel.yaml to get the tagged !vault scalar node
    snippet_yaml = YAML(typ="rt")
    encrypted_doc = snippet_yaml.load(snippet_text) or CommentedMap()
    encrypted_value = encrypted_doc.get("ansible_become_password")
    if encrypted_value is None:
        raise SystemExit(
            "Failed to parse 'ansible_become_password' from ansible-vault output."
        )

    # Store the vaulted value in host_vars
    doc["ansible_become_password"] = encrypted_value

    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)


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
    Parse a list of IDs supplied on the CLI. Supports:
      --include web-app-nextcloud web-app-mastodon
      --include web-app-nextcloud,web-app-mastodon
    Same logic is reused for --exclude and --roles.
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


def generate_random_password(length: int = 64) -> str:
    """
    Generate a random password using ASCII letters and digits.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# Inventory generation (servers.yml via build/inventory/full/__main__.py)
# ---------------------------------------------------------------------------


def generate_dynamic_inventory(
    host: str,
    roles_dir: Path,
    categories_file: Path,
    tmp_inventory: Path,
    project_root: Path,
) -> Dict[str, Any]:
    """
    Call `cli/build/inventory/full/__main__.py` directly to generate a dynamic inventory
    YAML for the given host and return it as a Python dict.
    """
    script = project_root / "cli" / "build" / "inventory" / "full/__main__.py"
    env = build_env_with_project_root(project_root)
    cmd = [
        sys.executable,
        str(script),
        "--host",
        host,
        "--format",
        "yaml",
        "--inventory-style",
        "group",
        "-c",
        str(categories_file),
        "-r",
        str(roles_dir),
        "-o",
        str(tmp_inventory),
    ]
    run_subprocess(cmd, capture_output=False, env=env)
    data = load_yaml(tmp_inventory)
    tmp_inventory.unlink(missing_ok=True)
    return data


def _filter_inventory_children(
    inv_data: Dict[str, Any],
    predicate,
) -> Dict[str, Any]:
    """
    Generic helper: keep only children for which predicate(group_name, group_data) is True.
    """
    all_block = inv_data.get("all", {})
    children = all_block.get("children", {}) or {}

    filtered_children: Dict[str, Any] = {}
    for group_name, group_data in children.items():
        if predicate(group_name, group_data):
            filtered_children[group_name] = group_data

    new_all = dict(all_block)
    new_all["children"] = filtered_children
    return {"all": new_all}


def filter_inventory_by_roles(
    inv_data: Dict[str, Any], roles_filter: Set[str]
) -> Dict[str, Any]:
    """
    Legacy: keep only groups whose names are in roles_filter.
    """
    return _filter_inventory_children(
        inv_data,
        lambda group_name, _group_data: group_name in roles_filter,
    )


def filter_inventory_by_include(
    inv_data: Dict[str, Any], include_set: Set[str]
) -> Dict[str, Any]:
    """
    Keep only groups whose names are in include_set.
    """
    return _filter_inventory_children(
        inv_data,
        lambda group_name, _group_data: group_name in include_set,
    )


def filter_inventory_by_ignore(
    inv_data: Dict[str, Any], ignore_set: Set[str]
) -> Dict[str, Any]:
    """
    Keep all groups except those whose names are in ignore_set.
    """
    return _filter_inventory_children(
        inv_data,
        lambda group_name, _group_data: group_name not in ignore_set,
    )


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
    primary_domain: Optional[str],
    ssl_disabled: bool,
    ip4: str,
    ip6: str,
) -> None:
    """
    Ensure host_vars/<host>.yml exists and contains base settings.

    Important: Existing keys are NOT overwritten. Only missing keys are added:
      - PRIMARY_DOMAIN (only if primary_domain is provided)
      - SSL_ENABLED   (true by default, false if --ssl-disabled is used)
      - networks.internet.ip4
      - networks.internet.ip6

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

    # Ensure local Ansible connection settings for local hosts.
    # This avoids SSH in CI containers (e.g. GitHub Actions) where no ssh client exists
    # and we want Ansible to execute tasks directly on the controller.
    local_hosts = {"localhost", "127.0.0.1", "::1"}

    if host in local_hosts:
        # Only set if not already defined, to avoid overwriting manual settings.
        if "ansible_connection" not in data:
            data["ansible_connection"] = "local"

    # Only set defaults; do NOT override existing values
    if primary_domain is not None and "PRIMARY_DOMAIN" not in data:
        data["PRIMARY_DOMAIN"] = primary_domain

    if "SSL_ENABLED" not in data:
        # By default SSL is enabled; --ssl-disabled flips this to false
        data["SSL_ENABLED"] = not ssl_disabled

    # networks.internet.ip4 / ip6
    networks = data.get("networks")
    if not isinstance(networks, CommentedMap):
        networks = CommentedMap()
        data["networks"] = networks

    internet = networks.get("internet")
    if not isinstance(internet, CommentedMap):
        internet = CommentedMap()
        networks["internet"] = internet

    if "ip4" not in internet:
        internet["ip4"] = ip4
    if "ip6" not in internet:
        internet["ip6"] = ip6

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


def get_path_administrator_home_from_group_vars(project_root: Path) -> str:
    """
    Read PATH_ADMINISTRATOR_HOME from group_vars/all/06_paths.yml.

    Expected layout (relative to project_root):

        group_vars/
          all/
            06_paths.yml

    If the file or variable is missing, fall back to '/home/administrator/'
    and emit a warning to stderr.
    """
    paths_file = project_root / "group_vars" / "all" / "06_paths.yml"
    default_path = "/home/administrator/"

    if not paths_file.exists():
        print(
            f"[WARN] group_vars paths file not found: {paths_file}. "
            f"Falling back to PATH_ADMINISTRATOR_HOME={default_path}",
            file=sys.stderr,
        )
        return default_path

    try:
        with paths_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:  # pragma: no cover
        print(
            f"[WARN] Failed to load {paths_file}: {exc}. "
            f"Falling back to PATH_ADMINISTRATOR_HOME={default_path}",
            file=sys.stderr,
        )
        return default_path

    value = data.get("PATH_ADMINISTRATOR_HOME", default_path)
    if not isinstance(value, str) or not value:
        print(
            f"[WARN] PATH_ADMINISTRATOR_HOME missing or invalid in {paths_file}. "
            f"Falling back to {default_path}",
            file=sys.stderr,
        )
        return default_path

    # Normalize: ensure it ends with exactly one trailing slash.
    value = value.rstrip("/") + "/"
    return value


def ensure_administrator_authorized_keys(
    inventory_dir: Path,
    host: str,
    authorized_keys_spec: Optional[str],
    project_root: Path,
) -> None:
    """
    Ensure that the administrator's authorized_keys file exists and contains
    all keys provided via --authorized-keys.

    Behavior:
      - If authorized_keys_spec is None → do nothing.
      - If authorized_keys_spec is a path to an existing file:
            read all non-empty, non-comment lines in that file as keys.
      - Else:
            treat authorized_keys_spec as literal key text, which may contain
            one or more keys separated by newlines.

    The target file path mirrors the Ansible task in roles/user-administrator:

        src: "{{ inventory_dir }}/files/{{ inventory_hostname }}{{ PATH_ADMINISTRATOR_HOME }}.ssh/authorized_keys"

    We implement the same pattern here:
        <inventory_dir>/files/<host><PATH_ADMINISTRATOR_HOME>.ssh/authorized_keys

    PATH_ADMINISTRATOR_HOME is read from group_vars/all/06_paths.yml so that
    Python and Ansible share a single source of truth.
    """
    if not authorized_keys_spec:
        return

    # Read PATH_ADMINISTRATOR_HOME from group_vars/all/06_paths.yml
    PATH_ADMINISTRATOR_HOME = get_path_administrator_home_from_group_vars(project_root)

    # Build relative path identical to the Ansible src:
    #   files/{{ inventory_hostname }}{{ PATH_ADMINISTRATOR_HOME }}.ssh/authorized_keys
    rel_fragment = f"{host}{PATH_ADMINISTRATOR_HOME}.ssh/authorized_keys"
    # remove leading slash so it becomes relative under files/
    rel_path = rel_fragment.lstrip("/")
    target_path = inventory_dir / "files" / rel_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    spec_path = Path(authorized_keys_spec)
    if spec_path.exists() and spec_path.is_file():
        # Use keys from the referenced file.
        source_text = spec_path.read_text(encoding="utf-8")
    else:
        # Treat the argument as literal key text.
        source_text = authorized_keys_spec

    # Normalize incoming keys: one key per non-empty, non-comment line.
    new_keys: List[str] = []
    for line in (source_text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        new_keys.append(stripped)

    if not new_keys:
        # Nothing to add.
        return

    existing_lines: List[str] = []
    existing_keys: Set[str] = set()

    if target_path.exists():
        for line in target_path.read_text(encoding="utf-8").splitlines():
            existing_lines.append(line)
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                existing_keys.add(stripped)

    # Append only keys that are not yet present (by stripped line match).
    for key in new_keys:
        if key not in existing_keys:
            existing_lines.append(key)
            existing_keys.add(key)

    # Write back, ensuring a trailing newline.
    final_text = "\n".join(existing_lines).rstrip() + "\n"
    target_path.write_text(final_text, encoding="utf-8")


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
        "-r",
        str(roles_dir),
    ]
    result = run_subprocess(cmd, capture_output=True, env=env)
    raw = (result.stdout or "").strip()

    if not raw:
        print(
            f"[WARN] Could not resolve role for application_id '{application_id}'. Skipping.",
            file=sys.stderr,
        )
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
        print(
            f"[WARN] Resolved role path does not exist: {role_path} (application_id={application_id})",
            file=sys.stderr,
        )
        return None

    return role_path


def fatal(msg: str) -> NoReturn:
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
        "--role-path",
        str(role_path),
        "--inventory-file",
        str(host_vars_file),
        "--vault-password-file",
        str(vault_password_file),
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
        print(
            "[WARN] No application_ids to process for credential generation.",
            file=sys.stderr,
        )
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
        if (
            "ansible_become_password" in snippet
            and "ansible_become_password" not in doc
        ):
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
        "inventory_dir",
        help="Inventory directory (e.g. inventories/galaxyserver).",
    )
    parser.add_argument(
        "--host",
        required=False,
        default="localhost",
        help="Hostname to use in the inventory (default: localhost).",
    )
    parser.add_argument(
        "--primary-domain",
        required=False,
        default=None,
        help="Primary domain for this host (e.g. infinito.nexus). Optional.",
    )
    parser.add_argument(
        "--ssl-disabled",
        action="store_true",
        help="Disable SSL for this host (sets SSL_ENABLED: false in host_vars).",
    )
    parser.add_argument(
        "--become-password",
        required=False,
        help=(
            "Optional become password. If omitted and ansible_become_password is "
            "missing, a random one is generated and vaulted. If omitted and "
            "ansible_become_password already exists, it is left unchanged."
        ),
    )
    parser.add_argument(
        "--authorized-keys",
        required=False,
        help=(
            "Optional SSH public keys for the 'administrator' account. "
            "May be a literal key string (possibly with newlines) or a path "
            "to a file containing one or more public keys. "
            "All keys are ensured to exist in "
            "files/<host><PATH_ADMINISTRATOR_HOME>.ssh/authorized_keys "
            "under the inventory directory; missing keys are appended."
        ),
    )
    parser.add_argument(
        "--vars",
        required=False,
        help=(
            "Optional JSON string with additional values for host_vars/<host>.yml. "
            "The JSON must have an object at the top level. All keys from this "
            "object (including nested ones) are merged into host_vars and "
            "overwrite existing values."
        ),
    )
    parser.add_argument(
        "--ip4",
        default="127.0.0.1",
        help="IPv4 address for networks.internet.ip4 (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--ip6",
        default="::1",
        help='IPv6 address for networks.internet.ip6 (default: "::1").',
    )
    parser.add_argument(
        "--inventory-file",
        help="Inventory YAML file path (default: <inventory-dir>/servers.yml).",
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        help=(
            "Optional legacy list of application_ids to include. "
            "Used only if neither --include nor --exclude is specified. "
            "Supports comma-separated values as well."
        ),
    )
    parser.add_argument(
        "--include",
        nargs="+",
        help=(
            "Only include the listed application_ids in the inventory. "
            "Mutually exclusive with --exclude."
        ),
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help=(
            "Exclude the listed application_ids from the inventory. "
            "Mutually exclusive with --include."
        ),
    )
    parser.add_argument(
        "--vault-password-file",
        required=False,
        default=None,
        help=(
            "Path to the Vault password file for credentials generation. "
            "If omitted, <inventory-dir>/.password is created or reused."
        ),
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

    # Parse include/exclude/roles lists
    include_filter = parse_roles_list(args.include)
    ignore_filter = parse_roles_list(args.exclude)
    roles_filter = parse_roles_list(args.roles)

    # Enforce mutual exclusivity: only one of --include / --exclude may be used
    if include_filter and ignore_filter:
        fatal(
            "Options --include and --exclude are mutually exclusive. Please use only one of them."
        )

    project_root = detect_project_root()
    roles_dir = Path(args.roles_dir) if args.roles_dir else (project_root / "roles")
    categories_file = (
        Path(args.categories_file)
        if args.categories_file
        else (roles_dir / "categories.yml")
    )

    inventory_dir = Path(args.inventory_dir).resolve()
    inventory_dir.mkdir(parents=True, exist_ok=True)

    inventory_file = (
        Path(args.inventory_file)
        if args.inventory_file
        else (inventory_dir / "servers.yml")
    )
    inventory_file = inventory_file.resolve()

    host_vars_dir = inventory_dir / "host_vars"
    host_vars_file = host_vars_dir / f"{args.host}.yml"

    # Vault password file: use provided one, otherwise create/reuse .password in inventory_dir
    if args.vault_password_file:
        vault_password_file = Path(args.vault_password_file).resolve()
    else:
        vault_password_file = inventory_dir / ".password"
        if not vault_password_file.exists():
            print(
                f"[INFO] No --vault-password-file provided. Creating {vault_password_file} ..."
            )
            password = generate_random_password()
            fd = os.open(
                str(vault_password_file),
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(password + "\n")
            try:
                vault_password_file.chmod(0o600)
            except PermissionError:
                # Best-effort; ignore if chmod is not allowed
                pass
        else:
            print(f"[INFO] Using existing vault password file: {vault_password_file}")

    tmp_inventory = inventory_dir / "_inventory_full_tmp.yml"

    # 1) Generate dynamic inventory via build/inventory/full/__main__.py
    print("[INFO] Generating dynamic inventory via cli/build/inventory/full/__main__.py ...")
    dyn_inv = generate_dynamic_inventory(
        host=args.host,
        roles_dir=roles_dir,
        categories_file=categories_file,
        tmp_inventory=tmp_inventory,
        project_root=project_root,
    )

    # 2) Apply filters: include → exclude → legacy roles
    if include_filter:
        print(
            f"[INFO] Including only application_ids: {', '.join(sorted(include_filter))}"
        )
        dyn_inv = filter_inventory_by_include(dyn_inv, include_filter)
    elif ignore_filter:
        print(f"[INFO] Ignoring application_ids: {', '.join(sorted(ignore_filter))}")
        dyn_inv = filter_inventory_by_ignore(dyn_inv, ignore_filter)
    elif roles_filter:
        print(
            f"[INFO] Filtering inventory to roles (legacy): {', '.join(sorted(roles_filter))}"
        )
        dyn_inv = filter_inventory_by_roles(dyn_inv, roles_filter)

    # Collect final application_ids from dynamic inventory for credential generation
    dyn_all = dyn_inv.get("all", {})
    dyn_children = dyn_all.get("children", {}) or {}
    application_ids = sorted(dyn_children.keys())

    if not application_ids:
        print(
            "[WARN] No application_ids found in dynamic inventory after filtering. Nothing to do.",
            file=sys.stderr,
        )

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
        ssl_disabled=args.ssl_disabled,
        ip4=args.ip4,
        ip6=args.ip6,
    )

    # 4b) Ensure ansible_become_password is vaulted according to CLI options
    print(f"[INFO] Ensuring ansible_become_password for host '{args.host}'")
    ensure_become_password(
        host_vars_file=host_vars_file,
        vault_password_file=vault_password_file,
        become_password=args.become_password,
    )

    # 4c) Ensure administrator authorized_keys file contains keys from --authorized-keys
    if args.authorized_keys:
        print(
            f"[INFO] Ensuring administrator authorized_keys for host '{args.host}' "
            f"from spec: {args.authorized_keys}"
        )
        ensure_administrator_authorized_keys(
            inventory_dir=inventory_dir,
            host=args.host,
            authorized_keys_spec=args.authorized_keys,
            project_root=project_root,
        )

    # 5) Generate credentials for all application_ids (snippets + single merge)
    if application_ids:
        print(
            f"[INFO] Generating credentials for {len(application_ids)} applications..."
        )
        generate_credentials_for_roles(
            application_ids=application_ids,
            roles_dir=roles_dir,
            host_vars_file=host_vars_file,
            vault_password_file=vault_password_file,
            project_root=project_root,
            workers=args.workers,
        )
    if args.vars:
        print(
            f"[INFO] Applying JSON overrides to host_vars for host '{args.host}' "
            f"via --vars"
        )
        apply_vars_overrides(
            host_vars_file=host_vars_file,
            json_str=args.vars,
        )

    print(
        "[INFO] Done. Inventory and host_vars updated without deleting existing values."
    )


if __name__ == "__main__":  # pragma: no cover
    main()
