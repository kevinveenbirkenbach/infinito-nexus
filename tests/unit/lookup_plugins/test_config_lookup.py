# tests/unit/lookup_plugins/test_config_lookup_unittest.py
from __future__ import annotations

import os
import unittest
from pathlib import Path

import yaml
from ansible.errors import AnsibleError

from lookup_plugins.config import LookupModule
from module_utils.config_utils import AppConfigKeyError, ConfigEntryNotSetError


def _write_schema(base_dir: Path, application_id: str, schema: dict) -> None:
    schema_path = base_dir / "roles" / application_id / "schema" / "main.yml"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(yaml.safe_dump(schema), encoding="utf-8")


class TestConfigLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.lm = LookupModule()

        # Create a temp working directory and chdir into it
        self._cwd = os.getcwd()
        self._tmp = Path(self._cwd) / ".tmp_test_config_lookup"
        if self._tmp.exists():
            # best-effort cleanup
            for p in sorted(self._tmp.rglob("*"), reverse=True):
                try:
                    p.unlink()
                except IsADirectoryError:
                    p.rmdir()
                except FileNotFoundError:
                    pass
            try:
                self._tmp.rmdir()
            except OSError:
                pass

        self._tmp.mkdir(parents=True, exist_ok=True)
        os.chdir(self._tmp)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        # best-effort cleanup
        if self._tmp.exists():
            for p in sorted(self._tmp.rglob("*"), reverse=True):
                try:
                    p.unlink()
                except IsADirectoryError:
                    p.rmdir()
                except FileNotFoundError:
                    pass
            try:
                self._tmp.rmdir()
            except OSError:
                pass

    def test_requires_2_or_3_terms(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lm.run([], variables={"applications": {}})
        with self.assertRaises(AnsibleError):
            self.lm.run(["a"], variables={"applications": {}})
        with self.assertRaises(AnsibleError):
            self.lm.run(["a", "b", "c", "d"], variables={"applications": {}})

    def test_requires_applications_var_present(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lm.run(["app", "x.y"], variables={})
        with self.assertRaises(AnsibleError):
            self.lm.run(["app", "x.y"], variables=None)

    def test_requires_applications_var_is_dict(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lm.run(
                ["app", "x.y"], variables={"applications": ["not", "a", "dict"]}
            )

    def test_returns_value_when_present(self) -> None:
        variables = {
            "applications": {"web-app-foo": {"smtp": {"host": "mail.example.org"}}}
        }
        out = self.lm.run(["web-app-foo", "smtp.host"], variables=variables)
        self.assertEqual(out, ["mail.example.org"])

    def test_strict_missing_key_raises_appconfigkeyerror(self) -> None:
        variables = {
            "applications": {"web-app-foo": {"smtp": {"host": "mail.example.org"}}}
        }
        with self.assertRaises(AppConfigKeyError):
            self.lm.run(["web-app-foo", "smtp.port"], variables=variables)

    def test_default_third_arg_disables_strict_and_returns_default(self) -> None:
        variables = {
            "applications": {"web-app-foo": {"smtp": {"host": "mail.example.org"}}}
        }
        out = self.lm.run(["web-app-foo", "smtp.port", 25], variables=variables)
        self.assertEqual(out, [25])

    def test_strict_missing_app_id_raises(self) -> None:
        variables = {
            "applications": {"web-app-foo": {"smtp": {"host": "mail.example.org"}}}
        }
        with self.assertRaises(AppConfigKeyError):
            self.lm.run(["web-app-missing", "smtp.host"], variables=variables)

    def test_schema_defined_but_unset_raises_configentrynotseterror(self) -> None:
        _write_schema(
            self._tmp,
            "web-app-foo",
            {"smtp": {"host": {}, "port": {}}},  # port is defined in schema
        )
        variables = {
            "applications": {"web-app-foo": {"smtp": {"host": "mail.example.org"}}}
        }
        with self.assertRaises(ConfigEntryNotSetError):
            self.lm.run(["web-app-foo", "smtp.port"], variables=variables)

    def test_index_access_supported(self) -> None:
        variables = {
            "applications": {
                "web-app-foo": {"hosts": ["a.example.org", "b.example.org"]}
            }
        }
        out = self.lm.run(["web-app-foo", "hosts[1]"], variables=variables)
        self.assertEqual(out, ["b.example.org"])

    def test_index_out_of_range_strict_raises(self) -> None:
        variables = {"applications": {"web-app-foo": {"hosts": ["a.example.org"]}}}
        with self.assertRaises(AppConfigKeyError):
            self.lm.run(["web-app-foo", "hosts[5]"], variables=variables)

    def test_index_out_of_range_with_default_returns_default(self) -> None:
        variables = {"applications": {"web-app-foo": {"hosts": ["a.example.org"]}}}
        out = self.lm.run(["web-app-foo", "hosts[5]", "fallback"], variables=variables)
        self.assertEqual(out, ["fallback"])


if __name__ == "__main__":
    unittest.main()
