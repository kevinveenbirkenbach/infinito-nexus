    # tests/unit/lookup_plugins/test_docker.py
import importlib.util
import os
import unittest
from pathlib import Path

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
    def setUpClass(cls) -> None:
        cls.mod = _load_module("lookup_plugins/docker.py", "lookup_plugins_docker")
        cls.LookupModule = cls.mod.LookupModule

    def setUp(self) -> None:
        # Ensure env is clean for tests that expect missing env.
        self._old_env = os.environ.get("PATH_DOCKER_COMPOSE_INSTANCES")
        if "PATH_DOCKER_COMPOSE_INSTANCES" in os.environ:
            del os.environ["PATH_DOCKER_COMPOSE_INSTANCES"]

    def tearDown(self) -> None:
        if self._old_env is None:
            os.environ.pop("PATH_DOCKER_COMPOSE_INSTANCES", None)
        else:
            os.environ["PATH_DOCKER_COMPOSE_INSTANCES"] = self._old_env

    def test_missing_path_in_vars_and_env_raises(self):
        lkp = self.LookupModule()
        with self.assertRaises(AnsibleError) as ctx:
            lkp.run(["svc-prx-openresty"], variables={})
        self.assertIn("PATH_DOCKER_COMPOSE_INSTANCES missing", str(ctx.exception))

    def test_uses_env_fallback_when_vars_missing(self):
        os.environ["PATH_DOCKER_COMPOSE_INSTANCES"] = "/opt/docker/"
        lkp = self.LookupModule()
        out = lkp.run(["svc-prx-openresty"], variables={})
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 1)

        dc = out[0]
        self.assertIsInstance(dc, dict)
        self.assertIn("directories", dc)
        self.assertIn("files", dc)

        # instance dir should start with base path
        self.assertTrue(dc["directories"]["instance"].startswith("/opt/docker/"))
        # and should include the entity name (likely "openresty")
        self.assertIn("openresty", dc["directories"]["instance"])

    def test_prefers_ansible_vars_over_env(self):
        os.environ["PATH_DOCKER_COMPOSE_INSTANCES"] = "/env/docker/"
        lkp = self.LookupModule()
        out = lkp.run(
            ["svc-prx-openresty"],
            variables={"PATH_DOCKER_COMPOSE_INSTANCES": "/vars/docker/"},
        )
        dc = out[0]
        self.assertTrue(dc["directories"]["instance"].startswith("/vars/docker/"))
        self.assertNotIn("/env/docker/", dc["directories"]["instance"])

    def test_explicit_second_term_overrides_vars_and_env(self):
        os.environ["PATH_DOCKER_COMPOSE_INSTANCES"] = "/env/docker/"
        lkp = self.LookupModule()
        out = lkp.run(
            ["svc-prx-openresty", "/explicit/docker/"],
            variables={"PATH_DOCKER_COMPOSE_INSTANCES": "/vars/docker/"},
        )
        dc = out[0]
        self.assertTrue(dc["directories"]["instance"].startswith("/explicit/docker/"))

    def test_application_id_is_stripped_and_validated(self):
        os.environ["PATH_DOCKER_COMPOSE_INSTANCES"] = "/opt/docker/"
        lkp = self.LookupModule()

        out = lkp.run(["  svc-prx-openresty  "], variables={})
        dc = out[0]
        self.assertIn("openresty", dc["directories"]["instance"])

        with self.assertRaises(AnsibleError):
            lkp.run(["   "], variables={})

    def test_path_instances_is_stripped_and_validated(self):
        lkp = self.LookupModule()

        out = lkp.run(
            ["svc-prx-openresty", "  /opt/docker/  "],
            variables={"PATH_DOCKER_COMPOSE_INSTANCES": "SHOULD_NOT_BE_USED"},
        )
        dc = out[0]
        self.assertTrue(dc["directories"]["instance"].startswith("/opt/docker/"))

        with self.assertRaises(AnsibleError):
            lkp.run(["svc-prx-openresty", "   "], variables={})


if __name__ == "__main__":
    unittest.main()
