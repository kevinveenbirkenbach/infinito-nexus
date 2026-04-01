from __future__ import annotations

import unittest
from pathlib import Path

import yaml


BOOTSTRAP_TASKS = (
    Path(__file__).resolve().parents[2]
    / "roles"
    / "web-app-pixelfed"
    / "tasks"
    / "00_bootstrap.yml"
)
MAIN_TASKS = (
    Path(__file__).resolve().parents[2]
    / "roles"
    / "web-app-pixelfed"
    / "tasks"
    / "main.yml"
)
COMPOSE_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "roles"
    / "web-app-pixelfed"
    / "templates"
    / "compose.yml.j2"
)


class TestPixelfedBootstrapWait(unittest.TestCase):
    def test_waits_for_entrypoint_bootstrap_before_running_artisan_bootstrap(self):
        content = BOOTSTRAP_TASKS.read_text(encoding="utf-8")

        self.assertIn(
            "Wait until the Pixelfed application container finished its entrypoint bootstrap",
            content,
        )
        self.assertIn('grep -q "apache2 -DFOREGROUND"', content)

        wait_index = content.index(
            "Wait until the Pixelfed application container finished its entrypoint bootstrap"
        )
        migrate_index = content.index("Run Pixelfed migrations")

        self.assertLess(wait_index, migrate_index)

    def test_bootstrap_marks_worker_ready_after_instance_setup(self):
        content = BOOTSTRAP_TASKS.read_text(encoding="utf-8")

        self.assertIn(
            "Mark Pixelfed bootstrap as complete for the worker container",
            content,
        )
        self.assertIn("/var/www/storage/.docker.init", content)

        instance_actor_index = content.index("Initialize the Pixelfed instance actor")
        marker_index = content.index(
            "Mark Pixelfed bootstrap as complete for the worker container"
        )

        self.assertLess(instance_actor_index, marker_index)

    def test_bootstrap_chooses_fresh_migration_for_incomplete_first_boot(self):
        content = BOOTSTRAP_TASKS.read_text(encoding="utf-8")

        self.assertIn("Check whether the Pixelfed bootstrap marker exists", content)
        self.assertIn("Check whether the Pixelfed users table exists", content)
        self.assertIn("Choose Pixelfed migration strategy", content)
        self.assertIn("migrate:fresh", content)
        self.assertIn("pixelfed_migrate_argv", content)

        strategy_index = content.index("Choose Pixelfed migration strategy")
        migrate_index = content.index("Run Pixelfed migrations")

        self.assertLess(strategy_index, migrate_index)

    def test_main_tasks_deploy_custom_entrypoint_before_flushing_compose(self):
        tasks = yaml.safe_load(MAIN_TASKS.read_text(encoding="utf-8"))
        content = MAIN_TASKS.read_text(encoding="utf-8")

        stack_task = next(
            task
            for task in tasks
            if task.get("name") == "load docker, db and proxy for {{ application_id }}"
        )
        self.assertEqual(stack_task["vars"]["docker_compose_flush_handlers"], False)
        self.assertIn("Deploy '{{ PIXELFED_ENTRYPOINT_HOST_ABS }}'", content)
        self.assertIn("Start Pixelfed containers with the repo-managed entrypoint", content)

        deploy_index = content.index("Deploy '{{ PIXELFED_ENTRYPOINT_HOST_ABS }}'")
        flush_index = content.index(
            "Start Pixelfed containers with the repo-managed entrypoint"
        )
        self.assertLess(deploy_index, flush_index)

    def test_compose_template_mounts_custom_application_entrypoint(self):
        content = COMPOSE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('entrypoint: "{{ PIXELFED_ENTRYPOINT_DOCKER }}"', content)
        self.assertIn(
            '"{{ PIXELFED_ENTRYPOINT_HOST_ABS }}:{{ PIXELFED_ENTRYPOINT_DOCKER }}:ro"',
            content,
        )


if __name__ == "__main__":
    unittest.main()
