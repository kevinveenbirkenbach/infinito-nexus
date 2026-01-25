# tests/unit/roles/docker-compose/files/test_compose_run.py
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def _repo_root(start: Path) -> Path:
    # __file__ = tests/unit/roles/docker-compose/files/test_compose_run.py
    return start.resolve().parents[5]


def _load_module(rel_path: str, name: str):
    root = _repo_root(Path(__file__))
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestComposeRun(unittest.TestCase):
    def setUp(self):
        self.m = _load_module(
            "roles/docker-compose/files/compose_run.py", "compose_run_mod"
        )

    @patch("subprocess.run", autospec=True)
    def test_config_action_calls_docker_compose_config(self, p_run):
        p_run.return_value.returncode = 0

        argv = [
            "compose_run.py",
            "--chdir",
            "/tmp/app",
            "--project",
            "p",
            "--compose-files",
            "-f a.yml -f b.yml",
            "--action",
            "config",
        ]
        with patch("sys.argv", argv):
            rc = self.m.main()

        self.assertEqual(rc, 0)
        called_cmd = p_run.call_args.args[0]
        self.assertEqual(called_cmd[:4], ["docker", "compose", "-p", "p"])
        self.assertIn("config", called_cmd)

    @patch("subprocess.run", autospec=True)
    def test_up_action_adds_detach_and_flags(self, p_run):
        p_run.return_value.returncode = 0

        argv = [
            "compose_run.py",
            "--chdir",
            "/tmp/app",
            "--project",
            "p",
            "--compose-files",
            "-f a.yml -f b.yml",
            "--action",
            "up",
            "--detach",
            "--up-flags",
            "--force-recreate --remove-orphans",
        ]
        with patch("sys.argv", argv):
            rc = self.m.main()

        self.assertEqual(rc, 0)
        called_cmd = p_run.call_args.args[0]
        self.assertIn("up", called_cmd)
        self.assertIn("-d", called_cmd)
        self.assertIn("--force-recreate", called_cmd)
        self.assertIn("--remove-orphans", called_cmd)


if __name__ == "__main__":
    unittest.main()
