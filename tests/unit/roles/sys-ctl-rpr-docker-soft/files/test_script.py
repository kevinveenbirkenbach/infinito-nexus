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

    def test_detect_env_file_priority(self):
        s = self.script
        base = "/proj"
        # Monkeypatch os.path.isfile
        old_isfile = s.os.path.isfile
        try:
            def fake_isfile(path):
                # Only .env exists
                return path == f"{base}/.env"
            s.os.path.isfile = fake_isfile
            self.assertEqual(s.detect_env_file(base), f"{base}/.env")

            # Only .env/env exists
            def fake_isfile2(path):
                return path == f"{base}/.env/env"
            s.os.path.isfile = fake_isfile2
            self.assertEqual(s.detect_env_file(base), f"{base}/.env/env")

            # Both exist -> prefer .env
            def fake_isfile3(path):
                return path in (f"{base}/.env", f"{base}/.env/env")
            s.os.path.isfile = fake_isfile3
            self.assertEqual(s.detect_env_file(base), f"{base}/.env")

            # Neither exists
            def fake_isfile4(path):
                return False
            s.os.path.isfile = fake_isfile4
            self.assertIsNone(s.detect_env_file(base))
        finally:
            s.os.path.isfile = old_isfile

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

    def test_main_restarts_and_counts_errors_and_envfile_usage(self):
        s = self.script
        cmd_log = []

        def fake_print_bash(cmd):
            cmd_log.append(cmd)

            # 1) docker ps Mocks (deine bisherigen)
            if cmd.startswith("docker ps --filter health=unhealthy"):
                return ["app1-web-1", "db-1"]
            if cmd.startswith("docker ps --filter status=exited"):
                return ["app1-worker-1", "other-2"]

            # 2) docker inspect Labels (NEU)
            # project label
            if cmd.startswith("docker inspect -f '{{ index .Config.Labels \"com.docker.compose.project\" }}'"):
                container = cmd.split()[-1]
                if container in ("app1-web-1", "app1-worker-1"):
                    return ["app1"]
                if container == "db-1":
                    return ["db"]
                return [""]  # other-2 hat keine Labels -> soll fehlschlagen

            # working_dir label
            if cmd.startswith("docker inspect -f '{{ index .Config.Labels \"com.docker.compose.project.working_dir\" }}'"):
                container = cmd.split()[-1]
                if container in ("app1-web-1", "app1-worker-1"):
                    return ["/BASE/app1"]
                if container == "db-1":
                    return ["/BASE/db"]
                return [""]  # other-2 -> keine Angabe

            # 3) docker-compose Aufrufe (unverändert okay)
            if "docker-compose" in cmd:
                return []

            return []

        # find_docker_compose_file wird in STRICT nicht benutzt, kann aber bleiben
        def fake_find_docker_compose(path):
            if path.endswith("/app1") or path.endswith("/db"):
                return str(Path(path) / "docker-compose.yml")
            return None

        # 4) os.path.isfile für STRICT mode (NEU)
        old_isfile = s.os.path.isfile
        def fake_isfile(path):
            return path in ("/BASE/app1/docker-compose.yml", "/BASE/db/docker-compose.yml")

        old_print_bash = s.print_bash
        old_find = s.find_docker_compose_file
        old_detect = s.detect_env_file
        try:
            s.print_bash = fake_print_bash
            s.find_docker_compose_file = fake_find_docker_compose
            s.detect_env_file = lambda project_path: (
                f"{project_path}/.env/env" if project_path.endswith("/app1")
                else (f"{project_path}/.env" if project_path.endswith("/db") else None)
            )
            s.os.path.isfile = fake_isfile  # <— wichtig für STRICT

            errors = s.main("/BASE", manipulation_services=[], timeout=None)

            # Erwartung: nur "other-2" scheitert -> 1 Fehler
            self.assertEqual(errors, 1)

            restart_cmds = [c for c in cmd_log if ' docker-compose' in c and " restart" in c]
            self.assertTrue(any(
                'cd "/BASE/app1"' in c and
                '--env-file "/BASE/app1/.env/env"' in c and
                '-p "app1"' in c and
                ' restart' in c
                for c in restart_cmds
            ))
            self.assertTrue(any(
                'cd "/BASE/db"' in c and
                '--env-file "/BASE/db/.env"' in c and
                '-p "db"' in c and
                ' restart' in c
                for c in restart_cmds
            ))
        finally:
            s.print_bash = old_print_bash
            s.find_docker_compose_file = old_find
            s.detect_env_file = old_detect
            s.os.path.isfile = old_isfile



if __name__ == "__main__":
    unittest.main()
