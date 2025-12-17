from ansible.errors import AnsibleFilterError
import os
import yaml


class FilterModule(object):
    def filters(self):
        return {
            'applications_if_group_and_deps': self.applications_if_group_and_deps,
        }

    def applications_if_group_and_deps(self, applications, group_names):
        """
        Return only those applications whose key is either:
          1) directly in group_names, or
          2) the application_id of any role reachable (recursively)
             from any group in group_names via meta/dependencies.
        """
        self._validate_inputs(applications, group_names)

        roles_dir = self._get_roles_directory()

        included_roles = self._collect_reachable_roles(group_names, roles_dir)
        included_app_ids = self._gather_application_ids(included_roles, roles_dir)

        return self._filter_applications(applications, group_names, included_app_ids)

    def _validate_inputs(self, applications, group_names):
        """Validate the inputs for correct types."""
        if not isinstance(applications, dict):
            raise AnsibleFilterError(f"Expected applications as dict, got {type(applications).__name__}")
        if not isinstance(group_names, (list, tuple)):
            raise AnsibleFilterError(f"Expected group_names as list/tuple, got {type(group_names).__name__}")

    def _get_roles_directory(self):
        """Locate and return the roles directory."""
        plugin_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(plugin_dir, '..'))
        return os.path.join(project_root, 'roles')

    def _collect_reachable_roles(self, group_names, roles_dir):
        """Recursively collect all roles reachable from the given groups via meta/dependencies."""
        included_roles = set()
        for group in group_names:
            self._collect_roles_from_group(group, included_roles, roles_dir)
        return included_roles

    def _collect_roles_from_group(self, group, seen, roles_dir):
        """Recursively collect roles from a specific group."""
        if group in seen:
            return
        seen.add(group)

        meta_file = os.path.join(roles_dir, group, 'meta', 'main.yml')
        if not os.path.isfile(meta_file):
            return

        try:
            with open(meta_file) as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            return

        for dep in meta.get('dependencies', []):
            dep_name = self._get_dependency_name(dep)
            if dep_name:
                self._collect_roles_from_group(dep_name, seen, roles_dir)

    def _get_dependency_name(self, dependency):
        """Extract the dependency role name from the meta data."""
        if isinstance(dependency, str):
            return dependency
        elif isinstance(dependency, dict):
            return dependency.get('role') or dependency.get('name')
        return None

    def _gather_application_ids(self, included_roles, roles_dir):
        """Gather application_ids from the roles."""
        included_app_ids = set()
        for role in included_roles:
            vars_file = os.path.join(roles_dir, role, 'vars', 'main.yml')
            if not os.path.isfile(vars_file):
                continue
            try:
                with open(vars_file) as f:
                    vars_data = yaml.safe_load(f) or {}
            except Exception:
                continue

            app_id = vars_data.get('application_id')
            if isinstance(app_id, str) and app_id:
                included_app_ids.add(app_id)

        return included_app_ids

    def _filter_applications(self, applications, group_names, included_app_ids):
        """Filter and return the applications that match the conditions."""
        result = {}
        for app_key, cfg in applications.items():
            if app_key in group_names or app_key in included_app_ids:
                result[app_key] = cfg
        return result
