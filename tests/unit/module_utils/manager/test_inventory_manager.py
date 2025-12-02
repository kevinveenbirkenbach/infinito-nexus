import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Make project root importable so that `module_utils` can be imported
ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../..")
)
sys.path.insert(0, ROOT_DIR)

from module_utils.manager.inventory import InventoryManager  # type: ignore
from module_utils.handler.vault import VaultScalar  # type: ignore


class TestInventoryManager(unittest.TestCase):
    def test_load_application_id_missing_exits(self):
        """
        If vars/main.yml does not contain application_id, InventoryManager
        must print an error and exit with code 1.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            role_path = Path(tmpdir) / "role"
            inv_path = Path(tmpdir) / "inventory.yml"

            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)

            # Dummy files so that Path comparisons in the fake loader work
            (role_path / "schema" / "main.yml").write_text("{}", encoding="utf-8")
            (role_path / "vars" / "main.yml").write_text("{}", encoding="utf-8")
            (role_path / "config" / "main.yml").write_text("{}", encoding="utf-8")
            inv_path.write_text("{}", encoding="utf-8")

            inventory_path = inv_path

            def fake_load_yaml(path):
                p = Path(path)
                if p == inventory_path:
                    return {}
                if p == role_path / "schema" / "main.yml":
                    return {}
                if p == role_path / "vars" / "main.yml":
                    # Missing application_id on purpose
                    return {}
                if p == role_path / "config" / "main.yml":
                    return {"features": {}}
                return {}

            with mock.patch(
                "module_utils.manager.inventory.YamlHandler.load_yaml",
                side_effect=fake_load_yaml,
            ), mock.patch(
                "module_utils.manager.inventory.VaultHandler"
            ):
                with self.assertRaises(SystemExit) as ctx:
                    InventoryManager(
                        role_path=role_path,
                        inventory_path=inventory_path,
                        vault_pw="dummy",
                        overrides={},
                    )
                self.assertEqual(ctx.exception.code, 1)

    def test_plain_without_override_and_allow_empty_plain_exits(self):
        """
        For a `plain` algorithm credential, if no override is provided and
        allow_empty_plain=False, recurse_credentials/apply_schema must exit.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            role_path = Path(tmpdir) / "role"
            inv_path = Path(tmpdir) / "inventory.yml"

            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)
            inv_path.write_text("{}", encoding="utf-8")

            inventory_path = inv_path

            schema_data = {
                "credentials": {
                    "api_key": {
                        "description": "API key",
                        "algorithm": "plain",
                        "validation": {},
                    }
                }
            }

            def fake_load_yaml(path):
                p = Path(path)
                if p == inventory_path:
                    return {"applications": {}}
                if p == role_path / "schema" / "main.yml":
                    return schema_data
                if p == role_path / "vars" / "main.yml":
                    return {"application_id": "app_test"}
                if p == role_path / "config" / "main.yml":
                    return {"features": {}}
                return {}

            with mock.patch(
                "module_utils.manager.inventory.YamlHandler.load_yaml",
                side_effect=fake_load_yaml,
            ), mock.patch(
                "module_utils.manager.inventory.VaultHandler"
            ):
                mgr = InventoryManager(
                    role_path=role_path,
                    inventory_path=inventory_path,
                    vault_pw="dummy",
                    overrides={},  # no plain override
                    allow_empty_plain=False,
                )
                with self.assertRaises(SystemExit) as ctx:
                    mgr.apply_schema()
                self.assertEqual(ctx.exception.code, 1)

    def test_plain_with_allow_empty_plain_sets_empty_string_unencrypted(self):
        """
        For a `plain` algorithm credential, if no override is provided and
        allow_empty_plain=True, the credential should be set to an empty string
        and must NOT be encrypted.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            role_path = Path(tmpdir) / "role"
            inv_path = Path(tmpdir) / "inventory.yml"

            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)
            inv_path.write_text("{}", encoding="utf-8")

            inventory_path = inv_path

            schema_data = {
                "credentials": {
                    "api_key": {
                        "description": "API key",
                        "algorithm": "plain",
                        "validation": {},
                    }
                }
            }

            def fake_load_yaml(path):
                p = Path(path)
                if p == inventory_path:
                    return {"applications": {}}
                if p == role_path / "schema" / "main.yml":
                    return schema_data
                if p == role_path / "vars" / "main.yml":
                    return {"application_id": "app_test"}
                if p == role_path / "config" / "main.yml":
                    return {"features": {}}
                return {}

            with mock.patch(
                "module_utils.manager.inventory.YamlHandler.load_yaml",
                side_effect=fake_load_yaml,
            ), mock.patch(
                "module_utils.manager.inventory.VaultHandler"
            ) as mock_vault_cls:
                # VaultHandler instance
                mock_vault = mock_vault_cls.return_value
                mock_vault.encrypt_string.return_value = "!vault |\n  $ANSIBLE_VAULT;1.1;AES256\n    ENCRYPTED"

                mgr = InventoryManager(
                    role_path=role_path,
                    inventory_path=inventory_path,
                    vault_pw="dummy",
                    overrides={},  # no override for plain
                    allow_empty_plain=True,
                )
                inv = mgr.apply_schema()

                apps = inv.get("applications", {})
                app_block = apps.get("app_test", {})
                creds = app_block.get("credentials", {})

                # api_key must be present and must be a literal empty string
                self.assertIn("api_key", creds)
                self.assertEqual(creds["api_key"], "")

                # Empty string must not trigger encryption
                mock_vault.encrypt_string.assert_not_called()

    def test_non_plain_algorithm_encrypts_and_sets_vaultscalar(self):
        """
        For non-plain algorithms, recurse_credentials must generate a value
        and encrypt it into a VaultScalar, unless an existing VaultScalar
        is already present.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            role_path = Path(tmpdir) / "role"
            inv_path = Path(tmpdir) / "inventory.yml"

            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)
            inv_path.write_text("{}", encoding="utf-8")

            inventory_path = inv_path

            schema_data = {
                "credentials": {
                    "api_key": {
                        "description": "API key",
                        "algorithm": "random_hex_16",
                        "validation": {},
                    }
                }
            }

            def fake_load_yaml(path):
                p = Path(path)
                if p == inventory_path:
                    return {"applications": {}}
                if p == role_path / "schema" / "main.yml":
                    return schema_data
                if p == role_path / "vars" / "main.yml":
                    return {"application_id": "app_test"}
                if p == role_path / "config" / "main.yml":
                    return {"features": {}}
                return {}

            fake_snippet = "!vault |\n  $ANSIBLE_VAULT;1.1;AES256\n    ENCRYPTEDVALUE"

            with mock.patch(
                "module_utils.manager.inventory.YamlHandler.load_yaml",
                side_effect=fake_load_yaml,
            ), mock.patch(
                "module_utils.manager.inventory.VaultHandler"
            ) as mock_vault_cls, mock.patch.object(
                InventoryManager,
                "generate_value",
                return_value="PLAINVAL",
            ):
                mock_vault = mock_vault_cls.return_value
                mock_vault.encrypt_string.return_value = fake_snippet

                mgr = InventoryManager(
                    role_path=role_path,
                    inventory_path=inventory_path,
                    vault_pw="dummy",
                    overrides={},
                    allow_empty_plain=False,
                )
                inv = mgr.apply_schema()

                apps = inv.get("applications", {})
                app_block = apps.get("app_test", {})
                creds = app_block.get("credentials", {})

                self.assertIn("api_key", creds)
                value = creds["api_key"]

                # api_key must be a VaultScalar
                self.assertIsInstance(value, VaultScalar)
                # Its underlying body should contain the vault header line
                self.assertIn("$ANSIBLE_VAULT", str(value))

                # Encryption must have been called with generated plaintext and key
                mock_vault.encrypt_string.assert_called_once_with("PLAINVAL", "api_key")

    def test_recurse_skips_existing_dict_and_vaultscalar(self):
        """
        If the destination already contains:
          - a dict for a credential key, or
          - a VaultScalar for a credential key,
        recurse_credentials must skip re-encryption and leave existing values
        untouched.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            role_path = Path(tmpdir) / "role"
            inv_path = Path(tmpdir) / "inventory.yml"

            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)
            inv_path.write_text("{}", encoding="utf-8")

            inventory_path = inv_path

            # Existing credentials in inventory
            existing_vault = VaultScalar("EXISTING_BODY")
            existing_dict = {"nested": "value"}

            inventory_data = {
                "applications": {
                    "app_test": {
                        "credentials": {
                            "already_vaulted": existing_vault,
                            "complex": existing_dict,
                        }
                    }
                }
            }

            schema_data = {
                "credentials": {
                    "already_vaulted": {
                        "description": "Vaulted",
                        "algorithm": "random_hex_16",
                        "validation": {},
                    },
                    "complex": {
                        "description": "Complex dict",
                        "algorithm": "random_hex_16",
                        "validation": {},
                    },
                }
            }

            def fake_load_yaml(path):
                p = Path(path)
                if p == inventory_path:
                    return inventory_data
                if p == role_path / "schema" / "main.yml":
                    return schema_data
                if p == role_path / "vars" / "main.yml":
                    return {"application_id": "app_test"}
                if p == role_path / "config" / "main.yml":
                    return {"features": {}}
                return {}

            with mock.patch(
                "module_utils.manager.inventory.YamlHandler.load_yaml",
                side_effect=fake_load_yaml,
            ), mock.patch(
                "module_utils.manager.inventory.VaultHandler"
            ) as mock_vault_cls, mock.patch.object(
                InventoryManager,
                "generate_value",
                return_value="IGNORED",
            ):
                mock_vault = mock_vault_cls.return_value
                mock_vault.encrypt_string.side_effect = AssertionError(
                    "encrypt_string should not be called for existing VaultScalar/dict"
                )

                mgr = InventoryManager(
                    role_path=role_path,
                    inventory_path=inventory_path,
                    vault_pw="dummy",
                    overrides={},
                    allow_empty_plain=False,
                )
                inv = mgr.apply_schema()

                apps = inv.get("applications", {})
                app_block = apps.get("app_test", {})
                creds = app_block.get("credentials", {})

                # Both keys must still be present
                self.assertIn("already_vaulted", creds)
                self.assertIn("complex", creds)

                # Types and values must be preserved
                self.assertIs(creds["already_vaulted"], existing_vault)
                self.assertIs(creds["complex"], existing_dict)


if __name__ == "__main__":
    unittest.main()
