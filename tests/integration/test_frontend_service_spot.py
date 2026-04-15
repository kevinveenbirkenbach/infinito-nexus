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

        setup_server_base = next(
            (
                task
                for task in tasks
                if isinstance(task, dict) and task.get("name") == "Setup server base"
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

        self.assertIsNotNone(setup_server_base)
        self.assertIsNotNone(server_roles_index)
        self.assertIn(
            "sys-utils-service-loader",
            setup_server_base.get("loop", []),
        )

    def test_load_app_does_not_load_frontend_services(self):
        content = pathlib.Path("tasks/utils/load_app.yml").read_text(encoding="utf-8")
        self.assertNotIn("load_services", content)

    def test_frontend_service_loader_lives_in_role(self):
        self.assertTrue(
            pathlib.Path("roles/sys-utils-service-loader/tasks/main.yml").is_file()
        )
        self.assertTrue(
            pathlib.Path(
                "roles/sys-utils-service-loader/tasks/load_frontend_service.yml"
            ).is_file()
        )

    def test_sys_front_inj_all_no_longer_loads_services(self):
        content = pathlib.Path("roles/sys-front-inj-all/tasks/main.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("01_services.yml", content)

    def test_front_proxy_falls_back_to_canonical_port_and_domain(self):
        content = pathlib.Path("roles/sys-stk-front-proxy/tasks/main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "default((ports.localhost.http | default({})).get(application_id))",
            content,
        )
        self.assertIn(
            "domain | default(lookup('domain', application_id))",
            content,
        )


if __name__ == "__main__":
    unittest.main()
