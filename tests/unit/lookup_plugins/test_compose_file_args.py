# tests/unit/lookup_plugins/test_compose_file_args.py
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    # __file__ = tests/unit/lookup_plugins/test_compose_file_args.py
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
            "lookup_plugins/compose_file_args.py",
            "compose_file_args_mod",
        )
        self.lookup = self.m.LookupModule()

        # In real Ansible, LookupBase gets _loader/_templar injected.
        # For unit tests, set them to placeholders.
        self.lookup._loader = object()
        self.lookup._templar = object()

        # compose_file_args no longer reads variables['docker_compose'].
        # It builds docker_compose via get_docker_paths(application_id, DIR_COMPOSITIONS).
        self.vars = {
            "DIR_COMPOSITIONS": "/x/",
            "domains": {
                "web-app-a": "example.invalid",
            },
        }

    def _stub_get_docker_paths(self, application_id: str, base_dir: str) -> dict:
        # Keep structure identical to module_utils.docker_paths_utils.get_docker_paths()
        # but stable for unit tests.
        self.assertEqual(application_id, "web-app-a")
        self.assertEqual(base_dir, "/x/")
        return {
            "files": {
                "docker_compose": "/x/compose.yml",
                "docker_compose_override": "/x/compose.override.yml",
                "docker_compose_ca_override": "/x/compose.ca.override.yml",
            }
        }

    def test_includes_base_and_override_when_role_provides_override_and_tls_off(self):
        with (
            patch.object(
                self.m, "get_docker_paths", side_effect=self._stub_get_docker_paths
            ),
            patch.object(self.m, "_role_provides_override", return_value=True),
            patch.object(
                self.m.lookup_loader, "get", return_value=_TlsResolveStub(False, "off")
            ),
        ):
            out = self.lookup.run(["web-app-a"], variables=self.vars)[0]

        self.assertEqual(out, "-f /x/compose.yml -f /x/compose.override.yml")

    def test_includes_ca_override_when_self_signed_and_domain_exists(self):
        with (
            patch.object(
                self.m, "get_docker_paths", side_effect=self._stub_get_docker_paths
            ),
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
            "-f /x/compose.yml -f /x/compose.override.yml -f /x/compose.ca.override.yml",
        )

    def test_fails_when_ca_override_missing_but_required(self):
        def stub_missing_ca(application_id: str, base_dir: str) -> dict:
            return {
                "files": {
                    "docker_compose": "/x/compose.yml",
                    "docker_compose_override": "/x/compose.override.yml",
                    "docker_compose_ca_override": "",
                }
            }

        with (
            patch.object(self.m, "get_docker_paths", side_effect=stub_missing_ca),
            patch.object(self.m, "_role_provides_override", return_value=True),
            patch.object(
                self.m.lookup_loader,
                "get",
                return_value=_TlsResolveStub(True, "self_signed"),
            ),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-a"], variables=self.vars)

    def test_includes_only_base_when_role_does_not_provide_override(self):
        with (
            patch.object(
                self.m, "get_docker_paths", side_effect=self._stub_get_docker_paths
            ),
            patch.object(self.m, "_role_provides_override", return_value=False),
            patch.object(
                self.m.lookup_loader, "get", return_value=_TlsResolveStub(False, "off")
            ),
        ):
            out = self.lookup.run(["web-app-a"], variables=self.vars)[0]

        self.assertEqual(out, "-f /x/compose.yml")

    def test_requires_one_term(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run([], variables=self.vars)
        with self.assertRaises(AnsibleError):
            self.lookup.run(["a", "b"], variables=self.vars)

    def test_requires_path_docker_compose_instances(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["web-app-a"], variables={"domains": {"web-app-a": "example.invalid"}}
            )

    def test_requires_docker_compose_structure_from_get_docker_paths(self):
        # get_docker_paths returns non-dict -> must fail
        with (
            patch.object(self.m, "get_docker_paths", return_value="nope"),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-a"], variables=self.vars)

        # get_docker_paths returns dict but missing files -> must fail
        with (
            patch.object(self.m, "get_docker_paths", return_value={}),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-a"], variables=self.vars)

        # get_docker_paths returns dict with non-dict files -> must fail
        with (
            patch.object(self.m, "get_docker_paths", return_value={"files": "nope"}),
        ):
            with self.assertRaises(AnsibleError):
                self.lookup.run(["web-app-a"], variables=self.vars)


if __name__ == "__main__":
    unittest.main()
