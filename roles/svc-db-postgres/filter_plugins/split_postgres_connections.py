import os
import yaml
from ansible.errors import AnsibleFilterError

def _iter_role_vars_files(roles_dir):
    if not os.path.isdir(roles_dir):
        raise AnsibleFilterError(f"roles_dir not found: {roles_dir}")
    for name in os.listdir(roles_dir):
        role_path = os.path.join(roles_dir, name)
        if not os.path.isdir(role_path):
            continue
        vars_main = os.path.join(role_path, "vars", "main.yml")
        if os.path.isfile(vars_main):
            yield vars_main

def _is_postgres_role(vars_file):
    try:
        with open(vars_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # only count roles with explicit database_type: postgres in VARS
        return str(data.get("database_type", "")).strip().lower() == "postgres"
    except Exception:
        # ignore unreadable/broken YAML files quietly
        return False

def split_postgres_connections(total_connections, roles_dir="roles"):
    """
    Return an integer average: total_connections / number_of_roles_with_database_type_postgres.
    Uses max(count, 1) to avoid division-by-zero.
    """
    try:
        total = int(total_connections)
    except Exception:
        raise AnsibleFilterError(f"total_connections must be int-like, got: {total_connections!r}")

    count = sum(1 for vf in _iter_role_vars_files(roles_dir) if _is_postgres_role(vf))
    denom = max(count, 1)
    return max(1, total // denom)

def list_postgres_roles(roles_dir="roles"):
    """
    Helper: return a list of role names that declare database_type: postgres in vars/main.yml.
    """
    names = []
    if not os.path.isdir(roles_dir):
        return names
    for name in os.listdir(roles_dir):
        vars_main = os.path.join(roles_dir, name, "vars", "main.yml")
        if os.path.isfile(vars_main) and _is_postgres_role(vars_main):
            names.append(name)
    return names

class FilterModule(object):
    def filters(self):
        return {
            "split_postgres_connections": split_postgres_connections,
            "list_postgres_roles": list_postgres_roles,
        }
