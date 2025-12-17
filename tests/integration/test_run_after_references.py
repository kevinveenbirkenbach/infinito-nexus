import os
import unittest
import yaml


class TestRunAfterReferences(unittest.TestCase):
    """
    Integration test: ensure that every name listed under
    galaxy_info.run_after in each role's meta/main.yml
    corresponds to an existing role directory.
    """

    @classmethod
    def setUpClass(cls):
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        cls.roles_dir = os.path.join(repo_root, "roles")
        # collect all role names (folder names) in roles/
        cls.existing_roles = {
            name
            for name in os.listdir(cls.roles_dir)
            if os.path.isdir(os.path.join(cls.roles_dir, name))
        }

    def test_run_after_points_to_existing_roles(self):
        errors = []
        for role in sorted(self.existing_roles):
            meta_path = os.path.join(self.roles_dir, role, "meta", "main.yml")
            if not os.path.isfile(meta_path):
                # skip roles without a meta/main.yml
                continue

            with open(meta_path, "r") as f:
                data = yaml.safe_load(f) or {}

            run_after = data.get("galaxy_info", {}).get("run_after", [])
            for dep in run_after:
                if dep not in self.existing_roles:
                    errors.append(
                        f"Role '{role}' declares run_after: '{dep}', "
                        f"but '{dep}' is not a directory under roles/"
                    )

        if errors:
            self.fail(
                "Some run_after references are invalid:\n  " + "\n  ".join(errors)
            )


if __name__ == "__main__":
    unittest.main()
