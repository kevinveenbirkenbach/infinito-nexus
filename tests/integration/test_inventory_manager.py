# tests/integration/test_inventory_manager.py

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from module_utils.manager.inventory import InventoryManager  # type: ignore
from module_utils.handler.vault import VaultScalar  # type: ignore


class _FakeVaultHandler:
    """
    Fake VaultHandler for integration tests.
    Avoids calling ansible-vault / subprocess, but still returns a vault-like snippet
    that InventoryManager can parse into a VaultScalar body.
    """

    def __init__(self, vault_pw: str) -> None:
        self.vault_pw = vault_pw
        self.calls: list[tuple[str, str]] = []

    def encrypt_string(self, plaintext: str, key_name: str) -> str:
        self.calls.append((plaintext, key_name))

        # This format must have at least 2 lines after splitlines(),
        # because InventoryManager reads lines[1] for indent detection.
        return (
            f"!vault |\n  $ANSIBLE_VAULT;1.1;AES256\n    PLAIN:{key_name}:{plaintext}\n"
        )


class TestInventoryManagerIntegration(unittest.TestCase):
    def test_apply_schema_reads_real_files_and_writes_inventory_struct(self):
        """
        Integration-style test:
        - Writes real YAML files to disk
        - Uses real YamlHandler parsing
        - Patches only VaultHandler to avoid external ansible-vault calls
        - Verifies end-to-end: schema + config -> inventory applications/credentials
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            role_path = tmp / "roles" / "web-app-demo"
            role_path.mkdir(parents=True, exist_ok=True)
            (role_path / "schema").mkdir(parents=True, exist_ok=True)
            (role_path / "vars").mkdir(parents=True, exist_ok=True)
            (role_path / "config").mkdir(parents=True, exist_ok=True)

            inv_path = tmp / "inventory.yml"

            # inventory.yml
            inv_path.write_text(
                "applications: {}\n",
                encoding="utf-8",
            )

            # vars/main.yml
            (role_path / "vars" / "main.yml").write_text(
                'application_id: "web-app-demo"\n',
                encoding="utf-8",
            )

            # config/main.yml (enables feature-based plain injections)
            (role_path / "config" / "main.yml").write_text(
                "docker:\n"
                "  services:\n"
                "    database:\n"
                "      shared: true\n"
                "    oauth2:\n"
                "      enabled: true\n",
                encoding="utf-8",
            )

            # schema/main.yml (drives vaulted + plain behavior)
            (role_path / "schema" / "main.yml").write_text(
                "credentials:\n"
                "  api_key:\n"
                "    description: API key\n"
                "    algorithm: random_hex_16\n"
                "    validation: {}\n"
                "  plain_needed:\n"
                "    description: Needs override\n"
                "    algorithm: plain\n"
                "    validation: {}\n"
                "non_credentials:\n"
                "  flag: true\n",
                encoding="utf-8",
            )

            fake_vault = _FakeVaultHandler("pw")

            with mock.patch(
                "module_utils.manager.inventory.VaultHandler",
                side_effect=lambda pw: fake_vault,
            ):
                mgr = InventoryManager(
                    role_path=role_path,
                    inventory_path=inv_path,
                    vault_pw="pw",
                    overrides={"credentials.plain_needed": "OVERRIDE"},
                    allow_empty_plain=False,
                )

                inv = mgr.apply_schema()

            app = inv["applications"]["web-app-demo"]
            creds = app["credentials"]

            # Feature-based values should be present and plain strings
            self.assertIn("database_password", creds)
            self.assertIsInstance(creds["database_password"], str)
            self.assertNotIsInstance(creds["database_password"], VaultScalar)

            self.assertIn("oauth2_proxy_cookie_secret", creds)
            self.assertIsInstance(creds["oauth2_proxy_cookie_secret"], str)
            self.assertNotIsInstance(creds["oauth2_proxy_cookie_secret"], VaultScalar)

            # Schema-driven keys should be vaulted (VaultScalar)
            self.assertIn("api_key", creds)
            self.assertIsInstance(creds["api_key"], VaultScalar)
            self.assertIn("$ANSIBLE_VAULT", str(creds["api_key"]))
            self.assertIn("PLAIN:api_key:", str(creds["api_key"]))

            self.assertIn("plain_needed", creds)
            self.assertIsInstance(creds["plain_needed"], VaultScalar)
            self.assertIn("PLAIN:plain_needed:OVERRIDE", str(creds["plain_needed"]))

            # Non-credentials should be copied
            self.assertEqual(app["non_credentials"]["flag"], True)

            # Fake vault should have been called for vaulted schema keys only
            called_keys = [k for (_plain, k) in fake_vault.calls]
            self.assertIn("api_key", called_keys)
            self.assertIn("plain_needed", called_keys)


if __name__ == "__main__":
    unittest.main()
