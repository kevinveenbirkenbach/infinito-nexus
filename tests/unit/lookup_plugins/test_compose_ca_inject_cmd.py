# tests/unit/lookup_plugins/test_compose_ca_inject_cmd.py
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    # __file__ = tests/unit/lookup_plugins/test_compose_ca_inject_cmd.py
    return Path(__file__).resolve().parents[3]


def _load_module(rel_path: str, name: str):
    path = _repo_root() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestComposeCaInjectCmd(unittest.TestCase):
    def setUp(self):
        self.m = _load_module(
            "roles/docker-compose/lookup_plugins/compose_ca_inject_cmd.py",
            "compose_ca_inject_cmd_mod",
        )
        self.lookup = self.m.LookupModule()

        self.vars = {
            "docker_compose": {
                "directories": {"instance": "/opt/docker/app/"},
                "files": {
                    "env": "/opt/docker/app/.env/env",
                    "docker_compose": "/opt/docker/app/docker-compose.yml",
                    "docker_compose_override": "/opt/docker/app/docker-compose.override.yml",
                    "docker_compose_ca_override": "/opt/docker/app/docker-compose.ca.override.yml",
                },
            },
            "CA_TRUST": {
                "inject_script": "/etc/infinito.nexus/bin/compose_ca_inject.py",
                "cert_host": "/etc/infinito.nexus/ca/root-ca.crt",
                "wrapper_host": "/etc/infinito.nexus/bin/with-ca-trust.sh",
                "trust_name": "infinito.nexus",
            },
        }

    def _patch_compose_f_args(self, ret: str):
        fake = type(
            "FakeComposeFArgs",
            (),
            {"run": staticmethod(lambda terms, variables=None, **kwargs: [ret])},
        )()
        return patch.object(self.m.lookup_loader, "get", return_value=fake)

    def _patch_env_file_exists(self, exists: bool):
        """
        compose_ca_inject_cmd now checks env file existence via pathlib.Path.is_file().
        We patch Path.is_file so we can test both branches without touching the FS.

        We keep this narrowly scoped: only treat the configured env path as existing/not existing.
        """
        env_path = str(self.vars["docker_compose"]["files"]["env"])

        def _is_file_side_effect(p: Path) -> bool:
            try:
                return str(p) == env_path and exists
            except Exception:
                return False

        return patch.object(
            self.m.Path, "is_file", autospec=True, side_effect=_is_file_side_effect
        )

    def test_builds_command_string(self):
        """
        Old test retained, but adapted:
        - Previously expected --env-file unconditionally.
        - Now env-file is only included if it exists.
        Here we test the 'exists' branch to preserve the spirit of the old test.
        """
        with (
            patch.object(self.m, "get_entity_name", return_value="myproj"),
            self._patch_compose_f_args(
                "-f /opt/docker/app/docker-compose.yml -f /opt/docker/app/docker-compose.override.yml"
            ),
            self._patch_env_file_exists(True),
        ):
            out = self.lookup.run(["web-app-foo"], variables=self.vars)[0]

        self.assertIn("python3", out)
        self.assertIn("/etc/infinito.nexus/bin/compose_ca_inject.py", out)

        self.assertIn("--project", out)
        self.assertIn("'myproj'", out)

        self.assertIn("--compose-files", out)
        self.assertIn(
            "-f /opt/docker/app/docker-compose.yml -f /opt/docker/app/docker-compose.override.yml",
            out,
        )
        self.assertNotIn("docker-compose.ca.override.yml -f", out)

        # Updated behavior: --env-file is included only when present.
        self.assertIn("--env-file", out)
        self.assertIn("/opt/docker/app/.env/env", out)

        self.assertIn("--out", out)
        self.assertIn("'docker-compose.ca.override.yml'", out)

        self.assertIn("--ca-host", out)
        self.assertIn("/etc/infinito.nexus/ca/root-ca.crt", out)

        self.assertIn("--wrapper-host", out)
        self.assertIn("/etc/infinito.nexus/bin/with-ca-trust.sh", out)

        self.assertIn("--trust-name", out)
        self.assertIn("'infinito.nexus'", out)

    def test_env_file_is_omitted_when_missing(self):
        with (
            patch.object(self.m, "get_entity_name", return_value="myproj"),
            self._patch_compose_f_args("-f /opt/docker/app/docker-compose.yml"),
            self._patch_env_file_exists(False),
        ):
            out = self.lookup.run(["web-app-foo"], variables=self.vars)[0]

        self.assertNotIn("--env-file", out)
        self.assertNotIn("/opt/docker/app/.env/env", out)

    def test_env_file_is_included_when_present(self):
        with (
            patch.object(self.m, "get_entity_name", return_value="myproj"),
            self._patch_compose_f_args("-f /opt/docker/app/docker-compose.yml"),
            self._patch_env_file_exists(True),
        ):
            out = self.lookup.run(["web-app-foo"], variables=self.vars)[0]

        self.assertIn("--env-file", out)
        self.assertIn("/opt/docker/app/.env/env", out)

    def test_requires_application_id_term(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=self.vars)

        with self.assertRaises(AnsibleError):
            self.lookup.run(["a", "b"], variables=self.vars)

        with self.assertRaises(AnsibleError):
            self.lookup.run([""], variables=self.vars)

    def test_requires_project_non_empty(self):
        with patch.object(self.m, "get_entity_name", return_value=""):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-foo"], variables=self.vars)

    def test_requires_structures(self):
        v = dict(self.vars)
        del v["CA_TRUST"]
        with (
            patch.object(self.m, "get_entity_name", return_value="p"),
            self._patch_compose_f_args("-f /opt/docker/app/docker-compose.yml"),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-foo"], variables=v)

    def test_requires_docker_compose_variable(self):
        v = dict(self.vars)
        del v["docker_compose"]
        with (
            patch.object(self.m, "get_entity_name", return_value="p"),
            self._patch_compose_f_args("-f /opt/docker/app/docker-compose.yml"),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-foo"], variables=v)

    def test_requires_compose_f_args_non_empty(self):
        with (
            patch.object(self.m, "get_entity_name", return_value="p"),
            self._patch_compose_f_args(""),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-foo"], variables=self.vars)


if __name__ == "__main__":
    unittest.main()
