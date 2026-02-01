# tests/unit/roles/docker-compose-ca/files/test_compose_ca_inject.py
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


def _repo_root(start: Path) -> Path:
    # __file__ = tests/unit/roles/docker-compose-ca/files/test_compose_ca_inject.py
    return start.resolve().parents[5]


def _load_module(rel_path: str, name: str):
    root = _repo_root(Path(__file__))
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestComposeCaInject(unittest.TestCase):
    def setUp(self):
        self.m = _load_module(
            "roles/docker-compose-ca/files/compose_ca_inject.py",
            "compose_ca_inject_mod",
        )

    def test_normalize_cmd(self):
        self.assertEqual(self.m.normalize_cmd(["a", "b"]), ["a", "b"])
        self.assertEqual(self.m.normalize_cmd("echo hi"), ["/bin/sh", "-lc", "echo hi"])
        self.assertEqual(self.m.normalize_cmd(None), [])
        with self.assertRaises(SystemExit):
            self.m.normalize_cmd(123)

    def test_normalize_entrypoint(self):
        self.assertEqual(self.m.normalize_entrypoint(["a", "b"]), ["a", "b"])
        self.assertEqual(
            self.m.normalize_entrypoint("echo hi"), ["/bin/sh", "-lc", "echo hi"]
        )
        self.assertEqual(self.m.normalize_entrypoint(None), [])
        with self.assertRaises(SystemExit):
            self.m.normalize_entrypoint(123)

    def test_parse_yaml_requires_mapping(self):
        doc = self.m.parse_yaml("a: 1\n", "x")
        self.assertEqual(doc["a"], 1)

        with self.assertRaises(SystemExit):
            self.m.parse_yaml("- 1\n- 2\n", "x")

    def test_has_build(self):
        self.assertTrue(self.m._has_build({"build": {"context": "."}}))
        self.assertTrue(self.m._has_build({"build": "./"}))
        self.assertFalse(self.m._has_build({}))
        self.assertFalse(self.m._has_build({"build": None}))

    def test_find_builder_service_for_image(self):
        services = {
            "app": {"image": "custom:1", "build": {"context": "."}},
            "worker": {"image": "custom:1"},
            "other": {"image": "other:2", "build": {"context": "."}},
        }
        self.assertEqual(
            self.m._find_builder_service_for_image(image="custom:1", services=services),
            "app",
        )
        self.assertEqual(
            self.m._find_builder_service_for_image(
                image="missing:tag", services=services
            ),
            "",
        )
        self.assertEqual(
            self.m._find_builder_service_for_image(image="", services=services),
            "",
        )

    def test_ensure_image_available_builds_self_when_build_present(self):
        """
        If the service has build:, ensure_image_available should run
        `docker compose ... build <service>` (not pull).
        """
        calls = []

        def fake_run(cmd, *, cwd, env):
            calls.append(cmd)

            # docker image inspect <image>: first missing, second exists
            if cmd[:3] == ["docker", "image", "inspect"]:
                inspect_calls = [
                    c for c in calls if c[:3] == ["docker", "image", "inspect"]
                ]
                if len(inspect_calls) == 1:
                    return 1, "", "no such image"
                return 0, json.dumps([{"Config": {"Entrypoint": [], "Cmd": []}}]), ""

            # docker compose ... build app
            if cmd[:2] == ["docker", "compose"] and cmd[-2:] == ["build", "app"]:
                return 0, "built", ""

            # anything else
            return 1, "", "unexpected"

        base_cmd = ["docker", "compose", "-p", "p", "-f", "docker-compose.yml"]

        with patch.object(self.m, "run", side_effect=fake_run):
            self.m.ensure_image_available(
                service_name="app",
                svc={"image": "custom:1", "build": {"context": "."}},
                image="custom:1",
                services={"app": {"image": "custom:1", "build": {"context": "."}}},
                service_to_compose_cmd={"app": base_cmd},
                compose_base_cmd=base_cmd,
                cwd=Path("/tmp"),
                env={},
            )

        self.assertTrue(any(c[-2:] == ["build", "app"] for c in calls))
        self.assertFalse(any(c[-2:] == ["pull", "app"] for c in calls))

    def test_ensure_image_available_builds_builder_for_shared_image(self):
        """
        New robust logic:
        - 'worker' has no build but references image 'custom:1'
        - 'app' has build and same image 'custom:1'
        => should run `docker compose ... build app` and not pull worker.
        """
        calls = []

        services = {
            "app": {"image": "custom:1", "build": {"context": "."}},
            "worker": {"image": "custom:1"},
        }

        base_cmd = ["docker", "compose", "-p", "p", "-f", "docker-compose.yml"]
        service_to_cmd = {"app": base_cmd, "worker": base_cmd}

        def fake_run(cmd, *, cwd, env):
            calls.append(cmd)

            # docker image inspect: first missing, second exists
            if cmd[:3] == ["docker", "image", "inspect"]:
                inspect_calls = [
                    c for c in calls if c[:3] == ["docker", "image", "inspect"]
                ]
                if len(inspect_calls) == 1:
                    return 1, "", "no such image"
                return 0, json.dumps([{"Config": {"Entrypoint": [], "Cmd": []}}]), ""

            # build builder (app)
            if cmd[:2] == ["docker", "compose"] and cmd[-2:] == ["build", "app"]:
                return 0, "built", ""

            # if pull(worker) happens, that's wrong for this test; still return success
            if cmd[:2] == ["docker", "compose"] and cmd[-2:] == ["pull", "worker"]:
                return 0, "pulled", ""

            return 1, "", "unexpected"

        with patch.object(self.m, "run", side_effect=fake_run):
            self.m.ensure_image_available(
                service_name="worker",
                svc=services["worker"],
                image="custom:1",
                services=services,
                service_to_compose_cmd=service_to_cmd,
                compose_base_cmd=base_cmd,
                cwd=Path("/tmp"),
                env={},
            )

        self.assertTrue(any(c[-2:] == ["build", "app"] for c in calls))
        self.assertFalse(any(c[-2:] == ["pull", "worker"] for c in calls))

    def test_ensure_image_available_falls_back_to_pull_when_no_builder(self):
        """
        If there is no builder service for an image, fall back to pull(service).
        """
        calls = []

        services = {"worker": {"image": "registry.example/worker:1"}}
        base_cmd = ["docker", "compose", "-p", "p", "-f", "docker-compose.yml"]
        service_to_cmd = {"worker": base_cmd}

        def fake_run(cmd, *, cwd, env):
            calls.append(cmd)

            # image inspect: first missing, second exists after pull
            if cmd[:3] == ["docker", "image", "inspect"]:
                inspect_calls = [
                    c for c in calls if c[:3] == ["docker", "image", "inspect"]
                ]
                if len(inspect_calls) == 1:
                    return 1, "", "no such image"
                return 0, json.dumps([{"Config": {"Entrypoint": [], "Cmd": []}}]), ""

            # pull succeeds
            if cmd[:2] == ["docker", "compose"] and cmd[-2:] == ["pull", "worker"]:
                return 0, "pulled", ""

            return 1, "", "unexpected"

        with patch.object(self.m, "run", side_effect=fake_run):
            self.m.ensure_image_available(
                service_name="worker",
                svc=services["worker"],
                image=services["worker"]["image"],
                services=services,
                service_to_compose_cmd=service_to_cmd,
                compose_base_cmd=base_cmd,
                cwd=Path("/tmp"),
                env={},
            )

        self.assertTrue(any(c[-2:] == ["pull", "worker"] for c in calls))

    @patch.object(Path, "exists", autospec=True, return_value=True)
    @patch.object(Path, "is_dir", autospec=True, return_value=True)
    @patch.object(Path, "read_text", autospec=True)
    @patch.object(Path, "write_text", autospec=True)
    @patch.object(Path, "mkdir", autospec=True)
    def test_main_generates_override(
        self, _mkdir, _write_text, _read_text, _is_dir, _exists
    ):
        """
        main():
          - parses compose files to discover profiles
          - runs `docker compose ... config`
          - inspects images via `docker image inspect`
          - writes override with CA_TRUST_* envs
        """
        _read_text.return_value = "services:\n  app:\n    image: myimage:latest\n"

        def fake_run(cmd, *, cwd, env):
            # docker compose ... config
            if (
                len(cmd) >= 3
                and cmd[0:2] == ["docker", "compose"]
                and cmd[-1] == "config"
            ):
                yml = "services:\n  app:\n    image: myimage:latest\n"
                return 0, yml, ""

            # docker image inspect <image>
            if cmd[:3] == ["docker", "image", "inspect"]:
                json_out = json.dumps(
                    [{"Config": {"Entrypoint": ["/entry"], "Cmd": ["run"]}}]
                )
                return 0, json_out, ""

            return 1, "", "unexpected"

        with patch.object(self.m, "run", side_effect=fake_run):
            argv = [
                "compose_ca_inject.py",
                "--chdir",
                "/tmp/app",
                "--project",
                "p",
                "--compose-files",
                "-f docker-compose.yml -f docker-compose.override.yml",
                "--out",
                "docker-compose.ca.override.yml",
                "--ca-host",
                "/etc/infinito/ca/root-ca.crt",
                "--wrapper-host",
                "/etc/infinito/bin/with-ca-trust.sh",
                "--trust-name",
                "infinito.local",
            ]
            with patch("sys.argv", argv):
                rc = self.m.main()

        self.assertEqual(rc, 0)
        self.assertTrue(_write_text.called)

        # Optional sanity: ensure the written YAML contains CA_TRUST_NAME and trust-name value
        args, _kwargs = _write_text.call_args
        written = args[1] if len(args) > 1 else ""
        self.assertIn("CA_TRUST_NAME", written)
        self.assertIn("infinito.local", written)

    @patch.object(Path, "exists", autospec=True, return_value=True)
    @patch.object(Path, "is_dir", autospec=True, return_value=True)
    def test_main_requires_trust_name(self, _is_dir, _exists):
        argv = [
            "compose_ca_inject.py",
            "--chdir",
            "/tmp/app",
            "--project",
            "p",
            "--compose-files",
            "-f docker-compose.yml",
            "--out",
            "docker-compose.ca.override.yml",
            "--ca-host",
            "/etc/infinito/ca/root-ca.crt",
            "--wrapper-host",
            "/etc/infinito/bin/with-ca-trust.sh",
            # missing: --trust-name
        ]
        with patch("sys.argv", argv):
            with self.assertRaises(SystemExit):
                self.m.main()


if __name__ == "__main__":
    unittest.main()
