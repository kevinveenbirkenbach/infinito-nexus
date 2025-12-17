import os
import yaml

def get_all_invokable_apps(
    categories_file=None,
    roles_dir=None
):
    """
    Return all application_ids (or role names) for roles whose directory names match invokable paths from categories.yml.
    :param categories_file: Path to categories.yml (default: roles/categories.yml at project root)
    :param roles_dir: Path to roles directory (default: roles/ at project root)
    :return: List of application_ids (or role names)
    """
    # Resolve defaults
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(here, '..'))
    if not categories_file:
        categories_file = os.path.join(project_root, 'roles', 'categories.yml')
    if not roles_dir:
        roles_dir = os.path.join(project_root, 'roles')

    # Get invokable paths
    from filter_plugins.invokable_paths import get_invokable_paths
    invokable_paths = get_invokable_paths(categories_file)
    if not invokable_paths:
        return []

    result = []
    if not os.path.isdir(roles_dir):
        return []

    for role in sorted(os.listdir(roles_dir)):
        role_path = os.path.join(roles_dir, role)
        if not os.path.isdir(role_path):
            continue
        if any(role == p or role.startswith(p + '-') for p in invokable_paths):
            vars_file = os.path.join(role_path, 'vars', 'main.yml')
            if os.path.isfile(vars_file):
                try:
                    with open(vars_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f) or {}
                    app_id = data.get('application_id', role)
                except Exception:
                    app_id = role
            else:
                app_id = role
            result.append(app_id)
    return sorted(result)

class FilterModule(object):
    def filters(self):
        return {
            'get_all_invokable_apps': get_all_invokable_apps
        }
