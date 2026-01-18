from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .errors import CombinedResolutionError
from .role_introspection import (
    require_role_exists,
    load_run_after,
    load_dependencies_app_only,
)


@dataclass(frozen=True)
class RoleEdges:
    run_after: List[str]
    dependencies: List[str]


class CombinedResolver:
    """
    Resolve a combined prerequisite graph:
      prerequisites(role) = run_after(role) + dependencies(role)

    Notes:
    - run_after edges are always followed
    - dependency edges are followed only for application roles (filtered in loader)
    """

    def __init__(self) -> None:
        self._cache: Dict[str, RoleEdges] = {}

    def edges_for(self, role_name: str) -> RoleEdges:
        if role_name in self._cache:
            return self._cache[role_name]

        require_role_exists(role_name)

        ra = load_run_after(role_name)
        deps = load_dependencies_app_only(role_name)

        # Validate referenced roles exist (run_after must exist; deps already validated)
        for r in ra:
            require_role_exists(r)

        edges = RoleEdges(run_after=ra, dependencies=deps)
        self._cache[role_name] = edges
        return edges

    def resolve(self, start_role: str) -> List[str]:
        """
        Return prerequisites-first (topological) list, excluding start_role.
        Cycle detection is across the combined graph.
        """
        require_role_exists(start_role)

        visited: Set[str] = set()
        stack: List[str] = []
        out: List[str] = []

        def dfs(node: str) -> None:
            if node in stack:
                idx = stack.index(node)
                cycle = stack[idx:] + [node]
                raise CombinedResolutionError(
                    f"Circular dependency detected: {' -> '.join(cycle)}"
                )

            if node in visited:
                return

            visited.add(node)
            stack.append(node)

            edges = self.edges_for(node)

            # prerequisites: run_after first, then dependencies
            for dep in edges.run_after:
                dfs(dep)
            for dep in edges.dependencies:
                dfs(dep)

            stack.pop()

            if node != start_role:
                out.append(node)

        dfs(start_role)
        return out

    def resolve_with_edges(
        self, start_role: str
    ) -> Tuple[List[str], Dict[str, RoleEdges]]:
        """
        Convenience method for tree printing: returns (resolved_list, cache_snapshot).
        """
        resolved = self.resolve(start_role)
        return resolved, dict(self._cache)
