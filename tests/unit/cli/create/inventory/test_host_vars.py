import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cli.create.inventory.host_vars import apply_vars_overrides_from_file

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from cli.create.inventory.host_vars import (
    ensure_host_vars_file,
    apply_vars_overrides,
    ensure_become_password,
)


class TestHostVars(unittest.TestCase):
    def test_ensure_host_vars_file_preserves_vault_and_adds_defaults(self):
        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host = "localhost"
            host_vars_file = Path(tmpdir) / f"{host}.yml"

            initial_yaml = """\
secret: !vault |
  $ANSIBLE_VAULT;1.1;AES256
    ENCRYPTEDVALUE
existing_key: foo
"""
            host_vars_file.write_text(initial_yaml, encoding="utf-8")

            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host=host,
                primary_domain="example.org",
                ssl_disabled=False,
                ip4="127.0.0.1",
                ip6="::1",
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml_rt.load(f)

            self.assertIsInstance(data, CommentedMap)
            self.assertEqual(data["existing_key"], "foo")
            self.assertEqual(getattr(data["secret"], "tag", None), "!vault")

            self.assertEqual(data["DOMAIN_PRIMARY"], "example.org")
            self.assertTrue(data["TLS_ENABLED"])
            self.assertEqual(data["networks"]["internet"]["ip4"], "127.0.0.1")
            self.assertEqual(data["networks"]["internet"]["ip6"], "::1")

            # Second call must not overwrite defaults
            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host="other-host",
                primary_domain="other.example",
                ssl_disabled=True,
                ip4="10.0.0.1",
                ip6="::2",
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data2 = yaml_rt.load(f)

            self.assertEqual(data2["DOMAIN_PRIMARY"], "example.org")
            self.assertTrue(data2["TLS_ENABLED"])
            self.assertEqual(data2["networks"]["internet"]["ip4"], "127.0.0.1")
            self.assertEqual(data2["networks"]["internet"]["ip6"], "::1")

    def test_ensure_host_vars_file_sets_local_connection_for_localhost(self):
        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host = "localhost"
            host_vars_file = Path(tmpdir) / f"{host}.yml"
            host_vars_file.write_text("", encoding="utf-8")

            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host=host,
                primary_domain=None,
                ssl_disabled=False,
                ip4="127.0.0.1",
                ip6="::1",
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml_rt.load(f)

            self.assertEqual(data["ansible_connection"], "local")

    def test_apply_vars_overrides_deep_merge_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host_vars.yml"
            host_vars_file.write_text(
                yaml.safe_dump(
                    {
                        "networks": {"internet": {"ip4": "1.2.3.4", "ip6": "::1"}},
                        "TLS_ENABLED": True,
                    }
                ),
                encoding="utf-8",
            )

            apply_vars_overrides(
                host_vars_file,
                """
                {
                  "networks": { "internet": { "ip4": "10.0.0.10" } },
                  "TLS_ENABLED": false
                }
                """,
            )

            data = yaml.safe_load(host_vars_file.read_text(encoding="utf-8"))
            self.assertEqual(data["networks"]["internet"]["ip4"], "10.0.0.10")
            self.assertEqual(data["networks"]["internet"]["ip6"], "::1")
            self.assertIs(data["TLS_ENABLED"], False)

    def test_apply_vars_overrides_requires_object(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host_vars.yml"
            with self.assertRaises(SystemExit):
                apply_vars_overrides(host_vars_file, '["not-an-object"]')

    def test_ensure_become_password_keeps_existing_when_no_cli_password(self):
        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host.yml"
            vault_pw_file = Path(tmpdir) / ".password"
            vault_pw_file.write_text("dummy\n", encoding="utf-8")

            doc = CommentedMap()
            doc["ansible_become_password"] = "EXISTING_VALUE"
            with host_vars_file.open("w", encoding="utf-8") as f:
                yaml_rt.dump(doc, f)

            ensure_become_password(
                host_vars_file=host_vars_file,
                vault_password_file=vault_pw_file,
                become_password=None,
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml_rt.load(f)

            self.assertEqual(data["ansible_become_password"], "EXISTING_VALUE")

    def test_ensure_become_password_sets_vaulted_value_via_vault_handler(self):
        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host.yml"
            vault_pw_file = Path(tmpdir) / ".password"
            vault_pw_file.write_text("dummy\n", encoding="utf-8")

            vaulted_snippet = """\
ansible_become_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
    ENCRYPTEDVALUE
"""

            with patch("cli.create.inventory.host_vars.VaultHandler") as VH:
                inst = VH.return_value
                inst.encrypt_string.return_value = vaulted_snippet

                ensure_become_password(
                    host_vars_file=host_vars_file,
                    vault_password_file=vault_pw_file,
                    become_password="plain",
                )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml_rt.load(f)

            node = data["ansible_become_password"]
            self.assertEqual(getattr(node, "tag", None), "!vault")


def test_apply_vars_overrides_from_file_deep_merge_and_overwrite(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        host_vars_file = tmp / "host_vars.yml"
        host_vars_file.write_text(
            yaml.safe_dump(
                {
                    "networks": {"internet": {"ip4": "1.2.3.4", "ip6": "::1"}},
                    "TLS_ENABLED": True,
                    "nested": {"keep": "yes"},
                }
            ),
            encoding="utf-8",
        )

        vars_file = tmp / "vars.yml"
        vars_file.write_text(
            yaml.safe_dump(
                {
                    "networks": {"internet": {"ip4": "10.0.0.10"}},
                    "TLS_ENABLED": False,
                    "nested": {"newkey": "added"},
                }
            ),
            encoding="utf-8",
        )

        apply_vars_overrides_from_file(
            host_vars_file=host_vars_file, vars_file=vars_file
        )

        data = yaml.safe_load(host_vars_file.read_text(encoding="utf-8"))
        self.assertEqual(data["networks"]["internet"]["ip4"], "10.0.0.10")
        self.assertEqual(data["networks"]["internet"]["ip6"], "::1")
        self.assertIs(data["TLS_ENABLED"], False)
        self.assertEqual(data["nested"]["keep"], "yes")
        self.assertEqual(data["nested"]["newkey"], "added")
