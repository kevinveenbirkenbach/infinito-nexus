from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.applications.in_group_deps import applications_if_group_and_all_deps
from utils.service_registry import build_service_registry_from_applications


class LookupModule(LookupBase):
    """
    Return the current play application mapping using the shared resolver from
    utils/applications/in_group_deps.
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        applications = kwargs.get("applications", vars_.get("applications"))
        group_names = kwargs.get("group_names", vars_.get("group_names", []))
        if not isinstance(applications, dict):
            raise AnsibleError(
                "applications_current_play: required variable 'applications' must be a mapping"
            )

        project_root = self._get_project_root()
        roles_dir = os.path.join(project_root, "roles")
        service_registry = kwargs.get("service_registry")
        if service_registry is None:
            service_registry = build_service_registry_from_applications(applications)

        try:
            result = applications_if_group_and_all_deps(
                applications,
                group_names,
                project_root=project_root,
                roles_dir=kwargs.get("roles_dir", roles_dir),
                service_registry=kwargs.get("service_registry", service_registry),
                meta_deps_resolver=self._meta_deps,
            )
        except ValueError as exc:
            raise AnsibleError(f"applications_current_play: {exc}") from exc

        return [result]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_project_root(self) -> str:
        plugin_dir = os.path.dirname(__file__)
        return os.path.abspath(os.path.join(plugin_dir, "..", ".."))

    def _meta_deps(self, role: str, roles_dir: str) -> List[str]:
        meta_file = os.path.join(roles_dir, role, "meta", "main.yml")
        if not os.path.isfile(meta_file):
            return []
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            return []
        deps = []
        for dep in meta.get("dependencies", []):
            if isinstance(dep, str):
                deps.append(dep)
            elif isinstance(dep, dict):
                name = dep.get("role") or dep.get("name")
                if name:
                    deps.append(name)
        return deps
