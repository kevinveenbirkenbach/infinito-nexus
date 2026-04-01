import pathlib
import unittest

import yaml


class TestFrontendServiceSpot(unittest.TestCase):
    def test_service_registry_does_not_use_load_phase(self):
        service_registry = yaml.safe_load(
            pathlib.Path("group_vars/all/20_services.yml").read_text(encoding="utf-8")
        )["SERVICE_REGISTRY"]

        for key, entry in service_registry.items():
            with self.subTest(service=key):
                self.assertNotIn("load_phase", entry)

    def test_server_stage_loads_frontend_services_before_server_groups(self):
        tasks = yaml.safe_load(
            pathlib.Path("tasks/stages/02_server.yml").read_text(encoding="utf-8")
        )

        load_services_index = next(
            (
                idx
                for idx, task in enumerate(tasks)
                if isinstance(task, dict)
                and "load_services.yml" in str(task.get("include_tasks", ""))
            ),
            None,
        )
        server_roles_index = next(
            (
                idx
                for idx, task in enumerate(tasks)
                if isinstance(task, dict) and task.get("name") == "Include server roles"
            ),
            None,
        )

        self.assertIsNotNone(load_services_index)
        self.assertIsNotNone(server_roles_index)
        self.assertLess(load_services_index, server_roles_index)

    def test_load_app_does_not_load_frontend_services(self):
        content = pathlib.Path("tasks/utils/load_app.yml").read_text(encoding="utf-8")
        self.assertNotIn("load_services.yml", content)

    def test_frontend_service_loader_uses_utils_wrapper(self):
        content = pathlib.Path("tasks/utils/load_services.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tasks', 'utils', '_load_frontend_service.yml", content)
        self.assertNotIn(
            "roles', 'sys-front-inj-all', 'tasks', '_load_frontend_service.yml", content
        )

    def test_sys_front_inj_all_no_longer_loads_services(self):
        content = pathlib.Path("roles/sys-front-inj-all/tasks/main.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("01_services.yml", content)


if __name__ == "__main__":
    unittest.main()
