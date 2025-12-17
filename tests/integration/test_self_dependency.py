import os
import unittest
import yaml


class TestSelfDependency(unittest.TestCase):
    """
    Integration test: ensure no role lists itself in its own 'run_after'
    in meta/main.yml.
    """

    @classmethod
    def setUpClass(cls):
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        cls.roles_dir = os.path.join(repo_root, "roles")

    def test_no_self_in_run_after(self):
        for entry in os.listdir(self.roles_dir):
            role_path = os.path.join(self.roles_dir, entry)
            meta_file = os.path.join(role_path, "meta", "main.yml")
            if not os.path.isdir(role_path) or not os.path.isfile(meta_file):
                continue

            with open(meta_file, "r") as f:
                data = yaml.safe_load(f) or {}

            run_after = data.get("galaxy_info", {}).get("run_after", [])
            if entry in run_after:
                self.fail(
                    f"Role '{entry}' has a self-dependency in its run_after list "
                    f"in {meta_file}"
                )


if __name__ == "__main__":
    unittest.main()
