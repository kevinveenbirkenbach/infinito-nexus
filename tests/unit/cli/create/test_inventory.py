import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make cli module importable (same pattern as test_credentials.py)
dir_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../cli')
)
sys.path.insert(0, dir_path)

from cli.create.inventory import (  # type: ignore
    merge_inventories,
    ensure_host_vars_file,
    ensure_become_password,
)

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class TestCreateInventory(unittest.TestCase):
    def test_merge_inventories_adds_host_and_preserves_existing(self):
        """
        merge_inventories() must:
        - ensure the given host exists in every group of the new inventory,
        - keep existing hosts and their variables untouched,
        - copy host vars from the new inventory when available,
        - create missing groups and add the host.
        """
        host = "localhost"

        base = {
            "all": {
                "children": {
                    "web-app-nextcloud": {
                        "hosts": {
                            "oldhost": {"ansible_host": "1.2.3.4"},
                        }
                    },
                    "web-app-matomo": {
                        "hosts": {
                            "otherhost": {"ansible_host": "5.6.7.8"},
                        }
                    },
                }
            }
        }

        # New inventory with localhost defined in two groups
        new = {
            "all": {
                "children": {
                    "web-app-nextcloud": {
                        "hosts": {
                            "localhost": {"ansible_host": "127.0.0.1"},
                        }
                    },
                    "web-app-matomo": {
                        "hosts": {
                            "localhost": {},
                        }
                    },
                    # A new group with no hosts → merge_inventories must create hosts + localhost
                    "web-app-phpmyadmin": {}
                }
            }
        }

        merged = merge_inventories(base, new, host=host)
        children = merged["all"]["children"]

        # 1) Existing hosts must remain unchanged
        self.assertIn("oldhost", children["web-app-nextcloud"]["hosts"])
        self.assertIn("otherhost", children["web-app-matomo"]["hosts"])

        # 2) localhost must be inserted into all groups from `new`
        self.assertIn("localhost", children["web-app-nextcloud"]["hosts"])
        self.assertIn("localhost", children["web-app-matomo"]["hosts"])
        self.assertIn("localhost", children["web-app-phpmyadmin"]["hosts"])

        # 3) Host vars from the new inventory must be preserved
        self.assertEqual(
            children["web-app-nextcloud"]["hosts"]["localhost"],
            {"ansible_host": "127.0.0.1"},
        )
        # Empty dict stays empty
        self.assertEqual(
            children["web-app-matomo"]["hosts"]["localhost"],
            {},
        )
        # New group with no host vars receives an empty dict
        self.assertEqual(
            children["web-app-phpmyadmin"]["hosts"]["localhost"],
            {},
        )

    def test_ensure_host_vars_file_preserves_vault_and_adds_defaults(self):
        """
        ensure_host_vars_file() must:
        - load existing YAML containing a !vault tag without crashing,
        - preserve the !vault node including its tag,
        - keep existing keys untouched,
        - add PRIMARY_DOMAIN, SSL_ENABLED and networks.internet.ip4/ip6 only when missing,
        - not overwrite them on subsequent calls.
        """
        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host = "localhost"
            host_vars_dir = Path(tmpdir)
            host_vars_file = host_vars_dir / f"{host}.yml"

            # File containing a !vault tag to ensure ruamel loader works correctly
            initial_yaml = """\
secret: !vault |
  $ANSIBLE_VAULT;1.1;AES256
    ENCRYPTEDVALUE
existing_key: foo
"""

            host_vars_dir.mkdir(parents=True, exist_ok=True)
            host_vars_file.write_text(initial_yaml, encoding="utf-8")

            # Run ensure_host_vars_file (first time)
            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host=host,
                primary_domain="example.org",
                ssl_disabled=False,
                ip4="127.0.0.1",
                ip6="::1",
            )

            # Reload with ruamel.yaml to verify structure and tags
            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml_rt.load(f)

            self.assertIsInstance(data, CommentedMap)

            # Existing keys must remain
            self.assertIn("secret", data)
            self.assertIn("existing_key", data)
            self.assertEqual(data["existing_key"], "foo")

            # !vault tag must stay intact
            secret_node = data["secret"]
            self.assertEqual(getattr(secret_node, "tag", None), "!vault")

            # Default values must be added
            self.assertEqual(data["PRIMARY_DOMAIN"], "example.org")
            self.assertIn("SSL_ENABLED", data)
            self.assertTrue(data["SSL_ENABLED"])

            self.assertIn("networks", data)
            self.assertIsInstance(data["networks"], CommentedMap)
            self.assertIn("internet", data["networks"])
            self.assertIsInstance(data["networks"]["internet"], CommentedMap)

            internet = data["networks"]["internet"]
            self.assertEqual(internet["ip4"], "127.0.0.1")
            self.assertEqual(internet["ip6"], "::1")

            # A second call must NOT overwrite existing defaults
            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host="other-host",
                primary_domain="other.example",
                ssl_disabled=True,   # would switch to false if it overwrote
                ip4="10.0.0.1",
                ip6="::2",
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data2 = yaml_rt.load(f)

            # Values remain unchanged
            self.assertEqual(data2["PRIMARY_DOMAIN"], "example.org")
            self.assertTrue(data2["SSL_ENABLED"])

            internet2 = data2["networks"]["internet"]
            self.assertEqual(internet2["ip4"], "127.0.0.1")
            self.assertEqual(internet2["ip6"], "::1")


    def test_ensure_host_vars_file_sets_local_connection_for_localhost(self):
        """
        When the host is a local address (localhost / 127.0.0.1 / ::1),
        ensure_host_vars_file should automatically set:
          - ansible_connection: local

        It must also preserve existing keys and be idempotent on re-run.
        """

        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host = "localhost"
            host_vars_dir = Path(tmpdir)
            host_vars_file = host_vars_dir / f"{host}.yml"

            # Start with an empty file (no ansible_* keys defined).
            host_vars_dir.mkdir(parents=True, exist_ok=True)
            host_vars_file.write_text("", encoding="utf-8")

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

            # Local connection settings must be present
            self.assertIn("ansible_connection", data)
            self.assertEqual(data["ansible_connection"], "local")

            # Basic keys from previous test behaviour should still be set
            self.assertIn("SSL_ENABLED", data)
            self.assertTrue(data["SSL_ENABLED"])
            self.assertIn("networks", data)

            # Re-run to verify idempotency (should not change values)
            ensure_host_vars_file(
                host_vars_file=host_vars_file,
                host=host,
                primary_domain="other.example.org",
                ssl_disabled=True,
                ip4="10.0.0.1",
                ip6="::2",
            )

            with host_vars_file.open("r", encoding="utf-8") as f:
                data2 = yaml_rt.load(f)

            self.assertEqual(data2["ansible_connection"], "local")
            
    def test_ensure_become_password_keeps_existing_when_no_cli_password(self):
        """
        If no --become-password is provided and ansible_become_password already
        exists in host_vars, ensure_become_password must not overwrite it and
        must not attempt to generate or vault a new one.
        """

        yaml_rt = YAML(typ="rt")
        yaml_rt.preserve_quotes = True

        with tempfile.TemporaryDirectory() as tmpdir:
            host = "localhost"
            host_vars_dir = Path(tmpdir)
            host_vars_file = host_vars_dir / f"{host}.yml"
            vault_pw_file = host_vars_dir / ".password"

            # Create a dummy vault password file (not actually used in this test)
            vault_pw_file.write_text("dummy\n", encoding="utf-8")

            # Seed host_vars with an existing ansible_become_password value
            initial = CommentedMap()
            initial["ansible_become_password"] = "EXISTING_VALUE"
            with host_vars_file.open("w", encoding="utf-8") as f:
                yaml_rt.dump(initial, f)

            # Call helper WITHOUT an explicit become_password
            ensure_become_password(
                host_vars_file=host_vars_file,
                vault_password_file=vault_pw_file,
                become_password=None,
            )

            # Reload and verify ansible_become_password remains unchanged
            with host_vars_file.open("r", encoding="utf-8") as f:
                doc = yaml_rt.load(f)

            self.assertIsNotNone(doc)
            self.assertIn("ansible_become_password", doc)
            self.assertEqual(doc["ansible_become_password"], "EXISTING_VALUE")

if __name__ == "__main__":
    unittest.main()
