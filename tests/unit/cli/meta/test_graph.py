import unittest
import tempfile
import shutil
import os
import yaml
from cli.build import graph


class TestGraphLogic(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.role_name = "role_a"
        self.role_path = os.path.join(self.temp_dir, self.role_name)
        os.makedirs(os.path.join(self.role_path, "meta"))
        os.makedirs(os.path.join(self.role_path, "tasks"))

        # Write meta/main.yml
        with open(os.path.join(self.role_path, "meta", "main.yml"), "w") as f:
            yaml.dump(
                {
                    "galaxy_info": {"author": "tester", "run_after": []},
                    "dependencies": [],
                },
                f,
            )

        # Write tasks/main.yml
        with open(os.path.join(self.role_path, "tasks", "main.yml"), "w") as f:
            yaml.dump(
                [
                    {"include_role": "some_other_role"},
                    {"import_role": {"name": "another_role"}},
                ],
                f,
            )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_meta_returns_dict(self):
        meta_path = graph.find_role_meta(self.temp_dir, self.role_name)
        meta = graph.load_meta(meta_path)
        self.assertIsInstance(meta, dict)
        self.assertIn("galaxy_info", meta)

    def test_load_tasks_include_role(self):
        task_path = graph.find_role_tasks(self.temp_dir, self.role_name)
        includes = graph.load_tasks(task_path, "include_role")
        self.assertIn("some_other_role", includes)

    def test_build_mappings_structure(self):
        result = graph.build_mappings(self.role_name, self.temp_dir, max_depth=1)
        self.assertIsInstance(result, dict)
        for key in graph.ALL_KEYS:
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
