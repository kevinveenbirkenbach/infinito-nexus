# tests/unit/roles/sys-ctl-hlth-webserver/files/test_script.py
import os
import unittest
import importlib.util
from unittest.mock import patch


def load_module_from_path(mod_name: str, path: str):
    """Dynamically load a module from a filesystem path."""
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class TestStandaloneCheckerScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compute repo root: tests/unit/roles/sys-ctl-hlth-webserver/files/test_script.py → 5 levels up
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))
        cls.script_path = os.path.join(
            repo_root, "roles", "sys-ctl-hlth-webserver", "files", "script.py"
        )
        if not os.path.isfile(cls.script_path):
            raise FileNotFoundError(f"Cannot find script.py at {cls.script_path}")
        cls.script = load_module_from_path("health_script", cls.script_path)

    # ------------- JSON parsing ------------------

    def test_rejects_invalid_json(self):
        with self.assertRaises(SystemExit):
            self.script.main([
                "--expectations", '{"bad json": [200, 301]',  # missing closing brace
            ])

    def test_rejects_non_mapping_json(self):
        with self.assertRaises(SystemExit):
            self.script.main([
                "--expectations", '["not", "a", "mapping"]',
            ])

    # ------------- Happy path / mismatches -------

    @patch("requests.head")
    def test_all_ok_returns_zero(self, mock_head):
        def head_side_effect(url, allow_redirects=False, timeout=10):
            class R: pass
            r = R()
            domain = url.split("://", 1)[1]
            # both match expectations exactly
            mapping = {"ok1.example.org": 200, "ok2.example.org": 301}
            r.status_code = mapping.get(domain, 200)
            return r

        mock_head.side_effect = head_side_effect

        exp = {
            "ok1.example.org": [200, 302, 301],
            "ok2.example.org": [301],
        }
        exit_code = self.script.main([
            "--web-protocol", "https",
            "--expectations", self._to_json(exp),
        ])
        self.assertEqual(exit_code, 0)

    @patch("requests.head")
    def test_mismatches_counted(self, mock_head):
        def head_side_effect(url, allow_redirects=False, timeout=10):
            class R: pass
            r = R()
            domain = url.split("://", 1)[1]
            mapping = {"bad.example.org": 200, "ok301.example.org": 301}
            r.status_code = mapping.get(domain, 200)
            return r

        mock_head.side_effect = head_side_effect

        exp = {
            "bad.example.org":   [404],  # mismatch (got 200)
            "ok301.example.org": [301],  # OK
            "never.example.org": [200],  # will default to 200 in side effect? No mapping -> 200 -> OK
        }
        # Adjust side effect to ensure "never.example.org" is OK 200
        exit_code = self.script.main([
            "--expectations", self._to_json(exp),
        ])
        # only 'bad.example.org' mismatched
        self.assertEqual(exit_code, 1)

    @patch("requests.head")
    def test_non_list_values_sanitize_to_empty_and_fail(self, mock_head):
        # If a domain maps to a non-list, it becomes [] and is treated as a failure
        def head_side_effect(url, allow_redirects=False, timeout=10):
            class R: pass
            r = R()
            r.status_code = 200
            return r

        mock_head.side_effect = head_side_effect

        exp_json = '{"foo.example.org": "not-a-list", "bar.example.org": 200}'
        # Both entries get empty expectations -> 2 errors
        exit_code = self.script.main([
            "--expectations", exp_json,
        ])
        self.assertEqual(exit_code, 2)

    # ------------- Helpers -----------------------

    @staticmethod
    def _to_json(obj) -> str:
        import json
        return json.dumps(obj, separators=(",", ":"))


if __name__ == "__main__":
    unittest.main()
