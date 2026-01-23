# tests/unit/lookup_plugins/test_compose_ca_inject_cmd.py
import importlib.util
import unittest
from pathlib import Path

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
            },
        }

    def test_builds_command_string(self):
        out = self.lookup.run([], variables=self.vars, project="myproj")[0]

        self.assertIn("python3", out)
        self.assertIn("/etc/infinito.nexus/bin/compose_ca_inject.py", out)

        # Must include base + override only (NOT the CA override)
        self.assertIn("--compose-files", out)
        self.assertIn(
            "-f /opt/docker/app/docker-compose.yml -f /opt/docker/app/docker-compose.override.yml",
            out,
        )

        # Must include env-file, out basename, and CA args
        self.assertIn("--env-file", out)
        self.assertIn("--out", out)
        self.assertIn("docker-compose.ca.override.yml", out)

        self.assertIn("--ca-host", out)
        self.assertIn("/etc/infinito.nexus/ca/root-ca.crt", out)
        self.assertIn("--wrapper-host", out)
        self.assertIn("/etc/infinito.nexus/bin/with-ca-trust.sh", out)

    def test_requires_project_kwarg(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=self.vars)

        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=self.vars, project="")

    def test_requires_structures(self):
        v = dict(self.vars)
        del v["CA_TRUST"]
        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=v, project="p")


if __name__ == "__main__":
    unittest.main()
