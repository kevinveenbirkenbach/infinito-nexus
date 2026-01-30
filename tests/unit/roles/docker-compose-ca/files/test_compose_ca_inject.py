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

    @patch.object(Path, "exists", autospec=True, return_value=True)
    @patch.object(Path, "is_dir", autospec=True, return_value=True)
    @patch.object(Path, "read_text", autospec=True)
    @patch.object(Path, "write_text", autospec=True)
    @patch.object(Path, "mkdir", autospec=True)
    def test_main_generates_override(
        self, _mkdir, _write_text, _read_text, _is_dir, _exists
    ):
        """
        The implementation:
          - parses compose files to discover profiles (reads files from --compose-files)
          - runs `docker compose ... config` (default + per-profile)
          - inspects images via `docker image inspect`
          - writes an override that injects CA_TRUST_CERT + CA_TRUST_NAME

        Therefore we must:
          - provide readable compose file content (for profile discovery)
          - mock run() for compose config + image inspect
          - include the new required arg: --trust-name
        """

        # Content for compose files referenced by -f ... arguments (profile discovery).
        # Keep it minimal; no profiles needed, but valid YAML mapping with services.
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
                # compose_ca_inject expects `run()` to return stdout as JSON string here.
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

        # Optional extra sanity: ensure the override contains CA_TRUST_NAME
        # (We can't easily read the written content since write_text is mocked,
        # but we *can* inspect its call args.)
        args, kwargs = _write_text.call_args
        # signature: Path.write_text(self, data, encoding=...)
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
