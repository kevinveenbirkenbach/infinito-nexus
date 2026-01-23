# tests/unit/lookup_plugins/test_compose_f_args.py
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    # __file__ = tests/unit/lookup_plugins/test_compose_f_args.py
    return Path(__file__).resolve().parents[3]


def _load_module(rel_path: str, name: str):
    path = _repo_root() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class _TlsResolveStub:
    def __init__(self, enabled: bool, mode: str):
        self._enabled = enabled
        self._mode = mode

    def run(self, terms, variables=None, **kwargs):
        return [{"enabled": self._enabled, "mode": self._mode}]


class TestComposeFArgs(unittest.TestCase):
    def setUp(self):
        self.m = _load_module(
            "roles/docker-compose/lookup_plugins/compose_f_args.py",
            "compose_f_args_mod",
        )
        self.lookup = self.m.LookupModule()

        # In real Ansible, LookupBase gets _loader/_templar injected.
        # For unit tests, set them to placeholders.
        self.lookup._loader = object()
        self.lookup._templar = object()

        self.vars = {
            "docker_compose": {
                "files": {
                    "docker_compose": "/x/docker-compose.yml",
                    "docker_compose_override": "/x/docker-compose.override.yml",
                    "docker_compose_ca_override": "/x/docker-compose.ca.override.yml",
                }
            },
            "domains": {
                "web-app-a": "example.invalid",
            },
        }

    def test_includes_base_and_override_when_role_provides_override_and_tls_off(self):
        with (
            patch.object(self.m, "_role_provides_override", return_value=True),
            patch.object(
                self.m.lookup_loader, "get", return_value=_TlsResolveStub(False, "off")
            ),
        ):
            out = self.lookup.run(["web-app-a"], variables=self.vars)[0]

        self.assertEqual(
            out, "-f /x/docker-compose.yml -f /x/docker-compose.override.yml"
        )

    def test_includes_ca_override_when_self_signed_and_domain_exists(self):
        with (
            patch.object(self.m, "_role_provides_override", return_value=True),
            patch.object(
                self.m.lookup_loader,
                "get",
                return_value=_TlsResolveStub(True, "self_signed"),
            ),
        ):
            out = self.lookup.run(["web-app-a"], variables=self.vars)[0]

        self.assertEqual(
            out,
            "-f /x/docker-compose.yml -f /x/docker-compose.override.yml -f /x/docker-compose.ca.override.yml",
        )

    def test_fails_when_ca_override_missing_but_required(self):
        v = {
            "docker_compose": {
                "files": {
                    "docker_compose": "/x/docker-compose.yml",
                    "docker_compose_override": "/x/docker-compose.override.yml",
                    "docker_compose_ca_override": "",
                }
            },
            "domains": {
                "web-app-a": "example.invalid",
            },
        }

        with (
            patch.object(self.m, "_role_provides_override", return_value=True),
            patch.object(
                self.m.lookup_loader,
                "get",
                return_value=_TlsResolveStub(True, "self_signed"),
            ),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-a"], variables=v)

    def test_includes_only_base_when_role_does_not_provide_override(self):
        with (
            patch.object(self.m, "_role_provides_override", return_value=False),
            patch.object(
                self.m.lookup_loader, "get", return_value=_TlsResolveStub(False, "off")
            ),
        ):
            out = self.lookup.run(["web-app-a"], variables=self.vars)[0]

        self.assertEqual(out, "-f /x/docker-compose.yml")

    def test_requires_one_term(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=self.vars)
        with self.assertRaises(AnsibleError):
            self.lookup.run(["a", "b"], variables=self.vars)

    def test_requires_docker_compose_structure(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables={})

        with self.assertRaises(AnsibleError):
            self.lookup.run(["web-app-a"], variables={"docker_compose": "nope"})


if __name__ == "__main__":
    unittest.main()
