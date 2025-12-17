import os
import unittest
import yaml


class TestCategoriesInvokableExclusion(unittest.TestCase):
    def test_no_child_invokable_if_any_parent_is_invokable(self):
        """
        Verify that if any ancestor in the hierarchy is invokable,
        none of its descendants may be invokable.
        """
        # locate roles/categories.yml
        base_dir = os.path.dirname(__file__)
        yaml_path = os.path.abspath(
            os.path.join(base_dir, "..", "..", "roles", "categories.yml")
        )

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        violations = []

        def recurse(node: dict, path: list[str], ancestor_invokable: bool):
            for key, value in node.items():
                if not isinstance(value, dict):
                    continue

                is_invokable = value.get("invokable", False)
                current_path = path + [key]

                # Violation: a descendant is invokable despite an invokable ancestor
                if ancestor_invokable and is_invokable:
                    ancestor_name = ".".join(path) if path else "<root>"
                    violations.append(
                        f"{'.'.join(current_path)} is invokable, "
                        f"but its ancestor ({ancestor_name}) is also invokable."
                    )

                # Any_invokable = True if this node or any ancestor is invokable
                new_ancestor_flag = ancestor_invokable or is_invokable

                # Recurse into subcategories
                for subkey, subval in value.items():
                    if isinstance(subval, dict):
                        recurse({subkey: subval}, current_path, new_ancestor_flag)

        # start at top-level roles, with no invokable ancestor
        recurse(data.get("roles", {}), [], False)

        if violations:
            self.fail(
                "Found invokable descendants under invokable parents:\n"
                + "\n".join(violations)
            )


if __name__ == "__main__":
    unittest.main()
