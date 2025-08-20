#!/usr/bin/env python3
import os
import glob
import unittest
import yaml


def _safe_yaml_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
            # A tasks file can be a list (usual) or a dict (blocks, etc.)
            return doc
    except Exception as e:
        raise AssertionError(f"Failed to parse YAML: {path}\n{e}") from e


class TestSysServiceRequiresSystemServiceId(unittest.TestCase):
    def setUp(self):
        # Repo root = three levels up from this file: tests/integration/<this_file>.py
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.roles_dir = os.path.join(self.repo_root, "roles")
        self.assertTrue(os.path.isdir(self.roles_dir), f"'roles' directory not found at: {self.roles_dir}")

    def _iter_task_files(self, role_dir):
        tasks_dir = os.path.join(role_dir, "tasks")
        if not os.path.isdir(tasks_dir):
            return
        patterns = ["*.yml", "*.yaml"]
        for pattern in patterns:
            for path in glob.glob(os.path.join(tasks_dir, pattern)):
                yield path

        # also scan nested includes like tasks/**/*.yml
        for pattern in patterns:
            for path in glob.glob(os.path.join(tasks_dir, "**", pattern), recursive=True):
                yield path

    def _role_includes_sys_service(self, tasks_doc) -> bool:
        """
        Return True if any task includes:
          - include_role:
              name: sys-service
        """
        def check_task(task):
            if not isinstance(task, dict):
                return False
            if "include_role" not in task:
                return False
            inc = task.get("include_role")
            if isinstance(inc, dict):
                name = inc.get("name")
                return name == "sys-service"
            # Rare shorthand: include_role: sys-service  (not common, but just in case)
            if isinstance(inc, str):
                return inc.strip() == "sys-service"
            return False

        # tasks_doc can be a list, dict (with 'block'), or None
        if isinstance(tasks_doc, list):
            for t in tasks_doc:
                if check_task(t):
                    return True
                # handle blocks within list items
                if isinstance(t, dict) and "block" in t and isinstance(t["block"], list):
                    for bt in t["block"]:
                        if check_task(bt):
                            return True
        elif isinstance(tasks_doc, dict):
            # top-level block file (rare)
            if "block" in tasks_doc and isinstance(tasks_doc["block"], list):
                for bt in tasks_doc["block"]:
                    if check_task(bt):
                        return True
        return False

    def _vars_has_system_service_id(self, role_dir):
        vars_dir = os.path.join(role_dir, "vars")
        if not os.path.isdir(vars_dir):
            return (False, "vars/ directory not found")
        candidates = []
        candidates.extend(glob.glob(os.path.join(vars_dir, "main.yml")))
        candidates.extend(glob.glob(os.path.join(vars_dir, "main.yaml")))
        if not candidates:
            return
