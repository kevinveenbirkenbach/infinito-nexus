import unittest
import os
import yaml


def load_yaml_file(file_path):
    """Load a YAML file and return its content."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file) or {}


def get_meta_info(role_path):
    """Extract dependencies from the meta/main.yml of a role."""
    meta_file = os.path.join(role_path, "meta", "main.yml")
    if not os.path.isfile(meta_file):
        return []
    meta_data = load_yaml_file(meta_file)
    dependencies = meta_data.get("dependencies", [])
    return dependencies


def resolve_dependencies(roles_dir):
    """Resolve all role dependencies and detect circular dependencies."""
    visited = set()  # Tracks roles that have been processed

    def visit(role_path, stack):
        role_name = os.path.basename(role_path)

        # Check for circular dependencies (if role is already in the current stack)
        if role_name in stack:
            raise ValueError(
                f"Circular dependency detected: {' -> '.join(stack)} -> {role_name}"
            )

        # Check if role is already processed
        if role_name in visited:
            return []

        # Mark role as visited and add to stack
        visited.add(role_name)
        stack.append(role_name)

        # Get dependencies and resolve them
        dependencies = get_meta_info(role_path)
        for dep in dependencies:
            dep_path = os.path.join(roles_dir, dep)
            visit(dep_path, stack)  # Recurse into dependencies

        stack.pop()  # Remove the current role from the stack

    for role_name in os.listdir(roles_dir):
        role_path = os.path.join(roles_dir, role_name)
        if os.path.isdir(role_path):
            try:
                visit(role_path, [])  # Start recursion from this role
            except ValueError as e:
                raise ValueError(
                    f"Error processing role '{role_name}' at path '{role_path}': {str(e)}"
                )


class TestRoleDependencies(unittest.TestCase):
    def test_no_circular_dependencies(self):
        roles_dir = "roles"  # Path to the roles directory

        try:
            resolve_dependencies(roles_dir)
        except ValueError as e:
            self.fail(f"Circular dependency detected: {e}")

        # If no exception, the test passed
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
