import tempfile
import unittest
from pathlib import Path
import yaml
from cli.create.inventory import (  # type: ignore
    merge_inventories,
    ensure_host_vars_file,
    ensure_become_password,
    parse_roles_list,
    filter_inventory_by_include,
    get_path_administrator_home_from_group_vars,
    ensure_administrator_authorized_keys,
    apply_vars_overrides,
)

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class TestCreateInventory(unittest.TestCase):
    def test_parse_roles_list_supports_commas_and_spaces(self):
        """
        parse_roles_list() should:
        - return None for None or empty input,
        - split comma separated values,
        - strip whitespace,
        - deduplicate values.
        """
        self.assertIsNone(parse_roles_list(None))
        self.assertIsNone(parse_roles_list([]))

        roles = parse_roles_list(
            [
                "web-app-nextcloud, web-app-matomo",
                "web-app-phpmyadmin",
                "web-app-nextcloud",  # duplicate
            ]
        )

        self.assertIsInstance(roles, set)
        self.assertEqual(
            roles,
            {"web-app-nextcloud", "web-app-matomo", "web-app-phpmyadmin"},
        )

    def test_filter_inventory_by_include_keeps_only_selected_groups(self):
        """
        filter_inventory_by_include() must:
        - keep only groups whose names are in the include set,
        - preserve the original group data for kept groups,
        - remove groups not listed in the include set.
        """
        original_inventory = {
            "all": {
                "children": {
                    "web-app-nextcloud": {
                        "hosts": {"localhost": {"ansible_host": "127.0.0.1"}},
                    },
                    "web-app-matomo": {
                        "hosts": {"localhost": {"ansible_host": "127.0.0.2"}},
                    },
                    "web-app-phpmyadmin": {
                        "hosts": {"localhost": {"ansible_host": "127.0.0.3"}},
                    },
                }
            }
        }

        include_set = {"web-app-nextcloud", "web-app-phpmyadmin"}

        filtered = filter_inventory_by_include(original_inventory, include_set)
        children = filtered["all"]["children"]

        # Only the included groups must remain
        self.assertIn("web-app-nextcloud", children)
        self.assertIn("web-app-phpmyadmin", children)
        self.assertNotIn("web-app-matomo", children)

        # The content of the kept groups must be identical to the original
        self.assertEqual(
            children["web-app-nextcloud"],
            original_inventory["all"]["children"]["web-app-nextcloud"],
        )
        self.assertEqual(
            children["web-app-phpmyadmin"],
            original_inventory["all"]["children"]["web-app-phpmyadmin"],
        )

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
                    "web-app-phpmyadmin": {},
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
                ssl_disabled=True,  # would switch to false if it overwrote
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

    def test_get_path_administrator_home_from_group_vars_reads_value(self):
        """
        get_path_administrator_home_from_group_vars() must:
        - read PATH_ADMINISTRATOR_HOME from group_vars/all/06_paths.yml,
        - normalize it to have exactly one trailing slash.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create group_vars/all/06_paths.yml with a custom PATH_ADMINISTRATOR_HOME
            gv_dir = project_root / "group_vars" / "all"
            gv_dir.mkdir(parents=True, exist_ok=True)
            paths_file = gv_dir / "06_paths.yml"
            paths_file.write_text(
                'PATH_ADMINISTRATOR_HOME: "/custom/admin"\n',
                encoding="utf-8",
            )

            value = get_path_administrator_home_from_group_vars(project_root)
            # Must normalize to exactly one trailing slash
            self.assertEqual(value, "/custom/admin/")

    def test_get_path_administrator_home_from_group_vars_falls_back_if_missing(self):
        """
        If group_vars/all/06_paths.yml does not exist or does not define
        PATH_ADMINISTRATOR_HOME, the helper must fall back to '/home/administrator/'.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # No group_vars/all/06_paths.yml present
            value = get_path_administrator_home_from_group_vars(project_root)
            self.assertEqual(value, "/home/administrator/")

            # Now create an empty 06_paths.yml without PATH_ADMINISTRATOR_HOME
            gv_dir = project_root / "group_vars" / "all"
            gv_dir.mkdir(parents=True, exist_ok=True)
            paths_file = gv_dir / "06_paths.yml"
            paths_file.write_text("", encoding="utf-8")

            value2 = get_path_administrator_home_from_group_vars(project_root)
            self.assertEqual(value2, "/home/administrator/")

    def test_ensure_administrator_authorized_keys_uses_file_and_deduplicates(self):
        """
        ensure_administrator_authorized_keys() must:
        - read PATH_ADMINISTRATOR_HOME from group_vars/all/06_paths.yml,
        - treat authorized_keys_spec as file path when it exists,
        - append keys that are not yet present,
        - not duplicate existing keys.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Fake project_root with group_vars/all/06_paths.yml
            project_root = tmp / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            gv_dir = project_root / "group_vars" / "all"
            gv_dir.mkdir(parents=True, exist_ok=True)
            paths_file = gv_dir / "06_paths.yml"
            paths_file.write_text(
                'PATH_ADMINISTRATOR_HOME: "/home/administrator/"\n',
                encoding="utf-8",
            )

            # Inventory dir (separate from project_root, as in real usage)
            inventory_dir = tmp / "inventory"
            inventory_dir.mkdir(parents=True, exist_ok=True)

            host = "galaxyserver"

            # Prepare a source authorized_keys file with two keys
            keys_file = tmp / "keys.pub"
            key1 = "ssh-ed25519 AAAA... key1@example"
            key2 = "ssh-ed25519 AAAA... key2@example"
            keys_file.write_text(f"{key1}\n{key2}\n", encoding="utf-8")

            # Pre-create target file with key1 already present and a comment
            # Path must match: files/<host><PATH_ADMINISTRATOR_HOME>.ssh/authorized_keys
            # PATH_ADMINISTRATOR_HOME = /home/administrator/
            target_rel = f"{host}/home/administrator/.ssh/authorized_keys"
            target_path = inventory_dir / "files" / target_rel
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                f"# existing authorized_keys\n{key1}\n",
                encoding="utf-8",
            )

            # Run helper with spec pointing to the keys file
            ensure_administrator_authorized_keys(
                inventory_dir=inventory_dir,
                host=host,
                authorized_keys_spec=str(keys_file),
                project_root=project_root,
            )

            # Verify that file contains key1 only once and key2 appended
            content = target_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertIn("# existing authorized_keys", content)
            self.assertEqual(content.count(key1), 1)
            self.assertEqual(content.count(key2), 1)

    def test_ensure_administrator_authorized_keys_accepts_literal_keys_string(self):
        """
        When authorized_keys_spec is not a path to an existing file,
        ensure_administrator_authorized_keys() must treat it as literal content.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            project_root = tmp / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            gv_dir = project_root / "group_vars" / "all"
            gv_dir.mkdir(parents=True, exist_ok=True)
            paths_file = gv_dir / "06_paths.yml"
            paths_file.write_text(
                'PATH_ADMINISTRATOR_HOME: "/home/administrator/"\n',
                encoding="utf-8",
            )

            inventory_dir = tmp / "inventory"
            inventory_dir.mkdir(parents=True, exist_ok=True)

            host = "localhost"

            key1 = "ssh-rsa AAAA... literal1@example"
            key2 = "ssh-rsa AAAA... literal2@example"
            literal_spec = f"{key1}\n{key2}\n"

            ensure_administrator_authorized_keys(
                inventory_dir=inventory_dir,
                host=host,
                authorized_keys_spec=literal_spec,
                project_root=project_root,
            )

            # Target file should now exist with both keys
            target_rel = f"{host}/home/administrator/.ssh/authorized_keys"
            target_path = inventory_dir / "files" / target_rel
            self.assertTrue(target_path.exists())

            lines = [
                line.strip()
                for line in target_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            self.assertIn(key1, lines)
            self.assertIn(key2, lines)

    def test_apply_vars_overrides_sets_top_level_flag(self):
        """
        apply_vars_overrides() should create the host_vars file (if missing)
        and set a simple top-level flag like MASK_CREDENTIALS_IN_LOGS: false.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host_vars.yml"

            # File should not exist initially
            self.assertFalse(host_vars_file.exists())

            json_payload = '{"MASK_CREDENTIALS_IN_LOGS": false}'
            apply_vars_overrides(host_vars_file, json_payload)

            # File must now exist and contain the flag as a boolean
            self.assertTrue(host_vars_file.exists())
            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            self.assertIn("MASK_CREDENTIALS_IN_LOGS", data)
            self.assertIs(data["MASK_CREDENTIALS_IN_LOGS"], False)

    def test_apply_vars_overrides_nested_merge_and_overwrite(self):
        """
        apply_vars_overrides() must overwrite nested values but preserve
        unrelated keys, effectively doing a deep merge.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host_vars_nested.yml"

            original = {
                "networks": {
                    "internet": {
                        "ip4": "1.2.3.4",
                        "ip6": "::1",
                    }
                },
                "SSL_ENABLED": True,
            }
            host_vars_file.write_text(
                yaml.safe_dump(original),
                encoding="utf-8",
            )

            json_payload = """
            {
                "networks": {
                    "internet": {
                        "ip4": "10.0.0.10"
                    }
                },
                "SSL_ENABLED": false
            }
            """
            apply_vars_overrides(host_vars_file, json_payload)

            with host_vars_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Nested merge: ip4 overwritten, ip6 preserved
            self.assertEqual(data["networks"]["internet"]["ip4"], "10.0.0.10")
            self.assertEqual(data["networks"]["internet"]["ip6"], "::1")

            # Top-level boolean flag overwritten
            self.assertIs(data["SSL_ENABLED"], False)

    def test_apply_vars_overrides_requires_object(self):
        """
        apply_vars_overrides() must reject JSON that does not contain an
        object at the top level (e.g. an array) and exit with SystemExit.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            host_vars_file = Path(tmpdir) / "host_vars_invalid.yml"

            invalid_json = '["not-an-object"]'
            with self.assertRaises(SystemExit):
                apply_vars_overrides(host_vars_file, invalid_json)


if __name__ == "__main__":
    unittest.main()
