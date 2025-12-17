import unittest
import sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec


def load_script_module():
    """
    Import the script under test from roles/sys-ctl-rpr-docker-hard/files/script.py
    """
    test_file = Path(__file__).resolve()
    repo_root = test_file.parents[5]  # .../tests/unit/roles/sys-ctl-rpr-docker-hard/files -> repo root
    script_path = repo_root / "roles" / "sys-ctl-rpr-docker-hard" / "files" / "script.py"
    if not script_path.exists():
        raise FileNotFoundError(f"script.py not found at {script_path}")
    spec = spec_from_file_location("rpr_hard_script", str(script_path))
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


class TestRepairDockerHard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script_module()

    def test_detect_env_file_priority(self):
        s = self.script
        base = "/proj"
        old_isfile = s.os.path.isfile
        try:
            # only .env
            s.os.path.isfile = lambda p: p == f"{base}/.env"
            self.assertEqual(s.detect_env_file(base), f"{base}/.env")

            # only .env/env
            s.os.path.isfile = lambda p: p == f"{base}/.env/env"
            self.assertEqual(s.detect_env_file(base), f"{base}/.env/env")

            # both -> prefer .env
            s.os.path.isfile = lambda p: p in (f"{base}/.env", f"{base}/.env/env")
            self.assertEqual(s.detect_env_file(base), f"{base}/.env")

            # none
            s.os.path.isfile = lambda p: False
            self.assertIsNone(s.detect_env_file(base))
        finally:
            s.os.path.isfile = old_isfile

    def test_hard_restart_uses_envfile_and_cwd(self):
        s = self.script
        calls = []

        def fake_run(cmd, cwd=None, check=None):
            calls.append({"cmd": cmd, "cwd": cwd, "check": check})
            class R:
                pass
            return R()

        old_run = s.subprocess.run
        old_detect = s.detect_env_file
        try:
            s.subprocess.run = fake_run
            s.detect_env_file = lambda d: f"{d}/.env/env"  # erzwinge .env/env

            s.hard_restart_docker_services("/X/APP")

            # Wir erwarten zwei Aufrufe: docker-compose --env-file ... down / up -d
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["cwd"], "/X/APP")
            self.assertEqual(calls[1]["cwd"], "/X/APP")
            # down
            self.assertIn("docker-compose", calls[0]["cmd"])
            self.assertIn("--env-file", calls[0]["cmd"])
            self.assertIn("/X/APP/.env/env", calls[0]["cmd"])
            self.assertIn("down", calls[0]["cmd"])
            # up -d
            self.assertIn("docker-compose", calls[1]["cmd"])
            self.assertIn("--env-file", calls[1]["cmd"])
            self.assertIn("/X/APP/.env/env", calls[1]["cmd"])
            self.assertIn("up", calls[1]["cmd"])
            self.assertIn("-d", calls[1]["cmd"])
        finally:
            s.subprocess.run = old_run
            s.detect_env_file = old_detect

    def test_main_scans_parent_and_filters_only(self):
        s = self.script
        seen = {"scandir": [], "called": []}

        class FakeDirEntry:
            def __init__(self, path, is_dir=True):
                self.path = path
                self._is_dir = is_dir
            def is_dir(self):
                return self._is_dir

        def fake_scandir(parent):
            seen["scandir"].append(parent)
            return [
                FakeDirEntry(f"{parent}/app1"),
                FakeDirEntry(f"{parent}/app2"),
                FakeDirEntry(f"{parent}/notdir", is_dir=False),
            ]

        def fake_isdir(p):
            return p == "/PARENT"

        def fake_isfile(p):
            # Nur app2 hat docker-compose.yml
            return p in ("/PARENT/app2/docker-compose.yml",)

        def fake_hard_restart(dir_path):
            seen["called"].append(dir_path)

        old_scandir = s.os.scandir
        old_isdir = s.os.path.isdir
        old_isfile = s.os.path.isfile
        old_restart = s.hard_restart_docker_services
        try:
            s.os.scandir = fake_scandir
            s.os.path.isdir = fake_isdir
            s.os.path.isfile = fake_isfile
            s.hard_restart_docker_services = fake_hard_restart

            # Mit --only app2 -> nur app2 wird aufgerufen
            sys_argv = sys.argv
            sys.argv = ["x", "/PARENT", "--only", "app2"]
            s.main()
            self.assertEqual(seen["called"], ["/PARENT/app2"])
        finally:
            s.os.scandir = old_scandir
            s.os.path.isdir = old_isdir
            s.os.path.isfile = old_isfile
            s.hard_restart_docker_services = old_restart
            sys.argv = sys_argv


if __name__ == "__main__":
    unittest.main()
