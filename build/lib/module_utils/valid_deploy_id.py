# File: module_utils/valid_deploy_id.py
"""
Utility for validating deployment application IDs against defined roles and inventory.
"""
import os
import yaml
import glob
import configparser

from filter_plugins.get_all_application_ids import get_all_application_ids

class ValidDeployId:
    def __init__(self, roles_dir='roles'):
        # Load all known application IDs from roles
        self.valid_ids = set(get_all_application_ids(roles_dir))

    def validate(self, inventory_path, ids):
        """
        Validate a list of application IDs against both role definitions and inventory.
        Returns a dict mapping invalid IDs to their presence status.
        Example:
          {
            "app1": {"in_roles": False, "in_inventory": True},
            "app2": {"in_roles": True, "in_inventory": False}
          }
        """
        invalid = {}
        for app_id in ids:
            in_roles = app_id in self.valid_ids
            in_inventory = self._exists_in_inventory(inventory_path, app_id)
            if not (in_roles and in_inventory):
                invalid[app_id] = {
                    'in_roles': in_roles,
                    'in_inventory': in_inventory
                }
        return invalid

    def _exists_in_inventory(self, inventory_path, app_id):
        _, ext = os.path.splitext(inventory_path)
        if ext in ('.yml', '.yaml'):
            return self._search_yaml_keys(inventory_path, app_id)
        else:
            return self._search_ini_sections(inventory_path, app_id)

    def _search_ini_sections(self, inventory_path, app_id):
        """
        Manually parse INI inventory for sections and host lists.
        Returns True if app_id matches a section name or a host in a section.
        """
        present = False
        with open(inventory_path, 'r', encoding='utf-8') as f:
            current_section = None
            for raw in f:
                line = raw.strip()
                # Skip blanks and comments
                if not line or line.startswith(('#', ';')):
                    continue
                # Section header
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].strip()
                    if current_section == app_id:
                        return True
                    continue
                # Host or variable line under a section
                if current_section:
                    # Split on commas or whitespace
                    for part in [p.strip() for p in line.replace(',', ' ').split()]:
                        if part == app_id:
                            return True
        return False

    def _search_yaml_keys(self, inventory_path, app_id):
        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return self._find_key(data, app_id)

    def _find_key(self, node, key):  # recursive search
        if isinstance(node, dict):
            for k, v in node.items():
                # If key matches and maps to a dict or list, consider it present
                if k == key and isinstance(v, (dict, list)):
                    return True
                if self._find_key(v, key):
                    return True
        elif isinstance(node, list):
            for item in node:
                if self._find_key(item, key):
                    return True
        return False
