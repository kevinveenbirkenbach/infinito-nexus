# tests/unit/lookup_plugins/test_docker.py
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    # __file__ = tests/unit/lookup_plugins/test_docker.py
    return Path(__file__).resolve().parents[3]


def _load_module(rel_path: str, name: str):
    path = _repo_root() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestLookupDocker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module("lookup_plugins/docker.py", "lookup_plugins_docker")
        cls.LookupModule = cls.mod.LookupModule

    def setUp(self):
        self.lookup = self.LookupModule()
        self.vars_ok = {"PATH_DOCKER_COMPOSE_INSTANCES": "/opt/docker/"}

        self.fake_paths = {
            "directories": {
                "instance": "/opt/docker/app/",
                "env": "/opt/docker/app/.env/",
                "services": "/opt/docker/app/services/",
                "volumes": "/opt/docker/app/volumes/",
                "config": "/opt/docker/app/config/",
            },
            "files": {
                "env": "/opt/docker/app/.env/app.env",
                "docker_compose": "/opt/docker/app/docker-compose.yml",
                "docker_compose_override": "/opt/docker/app/docker-compose.override.yml",
                "dockerfile": "/opt/docker/app/Dockerfile",
            },
        }

    def test_returns_full_dict_when_only_application_id(self):
        with patch.object(
            self.mod, "get_docker_paths", return_value=self.fake_paths
        ) as p:
            out = self.lookup.run(["web-app-mailu"], variables=self.vars_ok)
            self.assertEqual(out, [self.fake_paths])
            p.assert_called_once_with("web-app-mailu", "/opt/docker/")

    def test_returns_deep_value_for_dotted_path(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            out = self.lookup.run(
                ["web-app-mailu", "directories.instance"], variables=self.vars_ok
            )
            self.assertEqual(out, ["/opt/docker/app/"])

            out = self.lookup.run(
                ["web-app-mailu", "files.env"], variables=self.vars_ok
            )
            self.assertEqual(out, ["/opt/docker/app/.env/app.env"])

    def test_rejects_non_dotted_path(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            with self.assertRaises(AnsibleError) as ctx:
                self.lookup.run(
                    ["web-app-mailu", "directories"], variables=self.vars_ok
                )
            self.assertIn("only dotted paths are allowed", str(ctx.exception))

    def test_invalid_dotted_path_raises(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            with self.assertRaises(AnsibleError) as ctx:
                self.lookup.run(
                    ["web-app-mailu", "directories.doesnotexist"],
                    variables=self.vars_ok,
                )
            self.assertIn("invalid path", str(ctx.exception))

            with self.assertRaises(AnsibleError) as ctx:
                self.lookup.run(
                    ["web-app-mailu", "directories.instance.foo"],
                    variables=self.vars_ok,
                )
            self.assertIn("invalid path", str(ctx.exception))

    def test_missing_instances_base_var_raises(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            with self.assertRaises(AnsibleError) as ctx:
                self.lookup.run(["web-app-mailu"], variables={})
            self.assertIn("PATH_DOCKER_COMPOSE_INSTANCES not set", str(ctx.exception))

    def test_empty_application_id_raises(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            with self.assertRaises(AnsibleError) as ctx:
                self.lookup.run(["   "], variables=self.vars_ok)
            self.assertIn("application_id is empty", str(ctx.exception))

    def test_wrong_arity_raises(self):
        with patch.object(self.mod, "get_docker_paths", return_value=self.fake_paths):
            with self.assertRaises(AnsibleError):
                self.lookup.run([], variables=self.vars_ok)

            with self.assertRaises(AnsibleError):
                self.lookup.run(["a", "b", "c"], variables=self.vars_ok)


if __name__ == "__main__":
    unittest.main()
