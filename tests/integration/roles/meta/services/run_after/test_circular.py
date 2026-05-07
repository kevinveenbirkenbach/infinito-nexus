import unittest
from pathlib import Path

# import the functions from your CLI script
from cli.build.role_include import build_dependency_graph, find_cycle


class TestCircularDependencies(unittest.TestCase):
    """
    Integration test: ensure there are no circular 'run_after' dependencies
    among the roles in the roles/ directory.
    """

    @classmethod
    def setUpClass(cls):
        # Determine the path to the repo root and the roles directory
        here = str(Path(str(Path(__file__).parent)).resolve())
        repo_root = str(
            Path(str(Path(here) / ".." / ".." / ".." / ".." / ".." / "..")).resolve()
        )
        cls.roles_dir = str(Path(repo_root) / "roles")

    def test_no_circular_dependencies(self):
        # Build the dependency graph using the real roles/
        _graph, _in_degree, roles = build_dependency_graph(self.roles_dir)

        # Attempt to find a cycle in the run_after mapping
        cycle = find_cycle(roles)

        if cycle:
            # Format cycle as "A -> B -> C -> A"
            cycle_str = " -> ".join(cycle)
            self.fail(f"Circular dependency detected among roles: {cycle_str}")

        # If no cycle, this assertion will pass
        self.assertIsNone(cycle, "Expected no circular dependencies")


if __name__ == "__main__":
    unittest.main()
