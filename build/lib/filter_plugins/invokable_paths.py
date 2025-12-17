import os
import yaml
from typing import Dict, List, Optional

def get_invokable_paths(
    roles_file: Optional[str] = None,
    suffix: Optional[str] = None
) -> List[str]:
    """
    Load nested roles YAML and return dash-joined paths where 'invokable' is True. Appends suffix if provided.
    """
    if not roles_file:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        roles_file = os.path.join(project_root, 'roles', 'categories.yml')

    try:
        with open(roles_file, 'r') as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"Roles file not found: {roles_file}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML {roles_file}: {e}")

    if not isinstance(data, dict):
        raise ValueError("YAML root is not a dictionary")

    roles = data
    if 'roles' in roles and isinstance(roles['roles'], dict) and len(roles) == 1:
        roles = roles['roles']

    def _recurse(subroles: Dict[str, dict], parent: List[str] = None) -> List[str]:
        parent = parent or []
        found: List[str] = []
        METADATA = {'title', 'description', 'icon', 'invokable'}

        for key, cfg in subroles.items():
            path = parent + [key]
            if cfg.get('invokable', False):
                p = '-'.join(path)
                if suffix:
                    p += suffix
                found.append(p)

            children = {
                ck: cv for ck, cv in cfg.items()
                if ck not in METADATA and isinstance(cv, dict)
            }
            if children:
                found.extend(_recurse(children, path))
        return found

    return _recurse(roles)


def get_non_invokable_paths(
    roles_file: Optional[str] = None,
    suffix: Optional[str] = None
) -> List[str]:
    """
    Load nested roles YAML and return dash-joined paths where 'invokable' is False or missing.
    Appends suffix if provided.
    """
    if not roles_file:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        roles_file = os.path.join(project_root, 'roles', 'categories.yml')

    try:
        with open(roles_file, 'r') as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"Roles file not found: {roles_file}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML {roles_file}: {e}")

    if not isinstance(data, dict):
        raise ValueError("YAML root is not a dictionary")

    roles = data
    if 'roles' in roles and isinstance(roles['roles'], dict) and len(roles) == 1:
        roles = roles['roles']

    def _recurse_non(subroles: Dict[str, dict], parent: List[str] = None) -> List[str]:
        parent = parent or []
        found: List[str] = []
        METADATA = {'title', 'description', 'icon', 'invokable'}

        for key, cfg in subroles.items():
            path = parent + [key]
            p = '-'.join(path)
            inv = cfg.get('invokable', False)
            if not inv:
                entry = p + (suffix or "")
                found.append(entry)

            children = {
                ck: cv for ck, cv in cfg.items()
                if ck not in METADATA and isinstance(cv, dict)
            }
            if children:
                found.extend(_recurse_non(children, path))
        return found

    return _recurse_non(roles)


class FilterModule:
    def filters(self):
        return {
            'invokable_paths': get_invokable_paths,
            'non_invokable_paths': get_non_invokable_paths
        }
