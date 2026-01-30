import unittest
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec


def load_script_module():
    """
    Import the script under test from roles/docker-compose/files/compose_base.py
    """
    test_file = Path(__file__).resolve()
    repo_root = test_file.parents[
        5
    ]  # .../tests/unit/roles/docker-compose/files -> repo root
    script_path = repo_root / "roles" / "docker-compose" / "files" / "compose_base.py"
    if not script_path.exists():
        raise FileNotFoundError(f"compose_base.py not found at {script_path}")
    spec = spec_from_file_location("compose_base", str(script_path))
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


class TestInfinitoComposeWrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script_module()

    def test_detect_env_file_priority(self):
        s = self.script
        base = Path("/proj")

        old_is_file = s.Path.is_file
        try:

            def fake_is_file(self: Path) -> bool:
                return str(self) == "/proj/.env"

            s.Path.is_file = fake_is_file  # type: ignore[assignment]
            self.assertEqual(s.detect_env_file(base), Path("/proj/.env"))

            def fake_is_file2(self: Path) -> bool:
                return str(self) == "/proj/.env/env"

            s.Path.is_file = fake_is_file2  # type: ignore[assignment]
            self.assertEqual(s.detect_env_file(base), Path("/proj/.env/env"))

            def fake_is_file3(self: Path) -> bool:
                return str(self) in ("/proj/.env", "/proj/.env/env")

            s.Path.is_file = fake_is_file3  # type: ignore[assignment]
            self.assertEqual(s.detect_env_file(base), Path("/proj/.env"))

            def fake_is_file4(self: Path) -> bool:
                return False

            s.Path.is_file = fake_is_file4  # type: ignore[assignment]
            self.assertIsNone(s.detect_env_file(base))
        finally:
            s.Path.is_file = old_is_file  # type: ignore[assignment]

    def test_detect_compose_files_includes_optional_in_order(self):
        s = self.script
        base = Path("/proj")

        old_is_file = s.Path.is_file
        try:

            def fake_is_file(self: Path) -> bool:
                if str(self) == "/proj/docker-compose.yml":
                    return True
                if str(self) == "/proj/docker-compose.override.yml":
                    return True
                if str(self) == "/proj/docker-compose.ca.override.yml":
                    return True
                return False

            s.Path.is_file = fake_is_file  # type: ignore[assignment]
            files = s.detect_compose_files(base)
            self.assertEqual(
                [str(p) for p in files],
                [
                    "/proj/docker-compose.yml",
                    "/proj/docker-compose.override.yml",
                    "/proj/docker-compose.ca.override.yml",
                ],
            )
        finally:
            s.Path.is_file = old_is_file  # type: ignore[assignment]

    def test_build_cmd_contains_env_and_files(self):
        s = self.script
        base = Path("/proj")

        old_is_file = s.Path.is_file
        try:

            def fake_is_file(self: Path) -> bool:
                if str(self) == "/proj/docker-compose.yml":
                    return True
                if str(self) == "/proj/docker-compose.override.yml":
                    return True
                if str(self) == "/proj/docker-compose.ca.override.yml":
                    return False
                if str(self) == "/proj/.env":
                    return True
                if str(self) == "/proj/.env/env":
                    return True
                return False

            s.Path.is_file = fake_is_file  # type: ignore[assignment]
            cmd = s.build_cmd("myproj", base, ["up", "-d"])

            self.assertEqual(cmd[:4], ["docker", "compose", "-p", "myproj"])
            self.assertIn("-f", cmd)
            self.assertIn("/proj/docker-compose.yml", cmd)
            self.assertIn("/proj/docker-compose.override.yml", cmd)
            self.assertNotIn("/proj/docker-compose.ca.override.yml", cmd)

            self.assertIn("--env-file", cmd)
            self.assertIn("/proj/.env", cmd)

            self.assertEqual(cmd[-2:], ["up", "-d"])
        finally:
            s.Path.is_file = old_is_file  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
