# tests/unit/filter_plugins/test_get_docker_paths.py
import unittest


class TestGetDockerPaths(unittest.TestCase):
    def test_get_docker_paths_uses_entity_name_and_builds_layout(self):
        import filter_plugins.get_docker_paths as m

        # Patch get_entity_name to avoid dependency on module_utils during this test.
        m.get_entity_name = lambda app_id: "myentity"

        out = m.get_docker_paths("web-app-anything", "/opt/docker/")
        self.assertEqual(out["directories"]["instance"], "/opt/docker/myentity/")
        self.assertEqual(out["files"]["env"], "/opt/docker/myentity/.env/env")
        self.assertEqual(
            out["files"]["docker_compose"], "/opt/docker/myentity/docker-compose.yml"
        )
        self.assertEqual(
            out["files"]["docker_compose_override"],
            "/opt/docker/myentity/docker-compose.override.yml",
        )
        self.assertEqual(
            out["files"]["docker_compose_ca_override"],
            "/opt/docker/myentity/docker-compose.ca.override.yml",
        )
        self.assertEqual(out["files"]["dockerfile"], "/opt/docker/myentity/Dockerfile")

        # Ensure required top-level keys exist
        self.assertIn("directories", out)
        self.assertIn("files", out)


if __name__ == "__main__":
    unittest.main()
