import unittest
import types
import sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec


def load_script_module():
    """
    Import the script under test from roles/sys-ctl-rpr-docker-soft/files/script.py
    """
    test_file = Path(__file__).resolve()
    repo_root = test_file.parents[5]  # .../tests/unit/roles/sys-ctl-rpr-docker-soft/files -> repo root
    script_path = repo_root / "roles" / "sys-ctl-rpr-docker-soft" / "files" / "script.py"
    if not script_path.exists():
        raise FileNotFoundError(f"script.py not found at {script_path}")
    spec = spec_from_file_location("rpr_soft_script", str(script_path))
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


class TestRepairDockerSoft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script_module()

    def test_normalize_services_arg(self):
        s = self.script
        self.assertEqual(
            s.normalize_services_arg(["svc-a.service", " ", "svc-b.service"], None),
            ["svc-a.service", "svc-b.service"],
        )
        self.assertEqual(
            s.normalize_services_arg(None, "svc-a.service   svc-b.service"),
            ["svc-a.service", "svc-b.service"],
        )
        self.assertEqual(
            s.normalize_services_arg(None, "svc-a.service, svc-b.service, svc-c.service"),
            ["svc-a.service", "svc-b.service", "svc-c.service"],
        )
        self.assertEqual(s.normalize_services_arg([], ""), [])

    def test_wait_while_manipulation_running_respects_timeout(self):
        s = self.script
        calls = {"checks": 0, "sleeps": 0}
        t = {"now": 0}

        def fake_run(cmd, shell):
            self.assertIn("systemctl is-active --quiet", cmd)
            calls["checks"] += 1
            return types.SimpleNamespace(returncode=0)

        def fake_sleep(_secs):
            calls["sleeps"] += 1

        def fake_time():
            # each call advances time by 610s
            t["now"] += 610
            return t["now"]

        old_run = s.subprocess.run
        old_sleep = s.time.sleep
        old_time = s.time.time
        try:
            s.subprocess.run = fake_run
            s.time.sleep = fake_sleep
            s.time.time = fake_time

            s.wait_while_manipulation_running(["svc-a", "svc-b"], waiting_time=600, timeout=1200)

            self.assertGreaterEqual(calls["sleeps"], 1)
            self.assertGreaterEqual(calls["checks"], 1)
        finally:
            s.subprocess.run = old_run
            s.time.sleep = old_sleep
            s.time.time = old_time

    def test_main_restarts_and_counts_errors(self):
        s = self.script
        cmd_log = []

        def fake_print_bash(cmd):
            cmd_log.append(cmd)
            if cmd.startswith("docker ps --filter health=unhealthy"):
                return ["app1-web-1", "db-1"]
            if cmd.startswith("docker ps --filter status=exited"):
                return ["app1-worker-1", "other-2"]
            if "docker-compose" in cmd:
                return []
            return []

        def fake_find_docker_compose(path):
            if path.endswith("/app1") or path.endswith("/db"):
                return str(Path(path) / "docker-compose.yml")
            return None

        old_print_bash = s.print_bash
        old_find = s.find_docker_compose_file
        try:
            s.print_bash = fake_print_bash
            s.find_docker_compose_file = fake_find_docker_compose  # <-- jetzt gleicher Name!

            errors = s.main("/BASE", manipulation_services=[], timeout=None)
            self.assertEqual(errors, 1)

            restart_cmds = [c for c in cmd_log if "docker-compose -p" in c and " restart" in c]
            self.assertTrue(any('cd "/BASE/app1"' in c and 'docker-compose -p "app1" restart' in c for c in restart_cmds))
            self.assertTrue(any('cd "/BASE/db"' in c and 'docker-compose -p "db" restart' in c for c in restart_cmds))
        finally:
            s.print_bash = old_print_bash
            s.find_docker_compose_file = old_find

if __name__ == "__main__":
    unittest.main()
