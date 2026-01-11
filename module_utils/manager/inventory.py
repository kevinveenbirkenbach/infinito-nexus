# module_utils/manager/inventory.py

from pathlib import Path
from typing import Dict, List
from module_utils.handler.yaml import YamlHandler
from module_utils.handler.vault import VaultHandler, VaultScalar
from module_utils.manager.value_generator import ValueGenerator
import sys


class InventoryManager:
    def __init__(
        self,
        role_path: Path,
        inventory_path: Path,
        vault_pw: str,
        overrides: Dict[str, str],
        allow_empty_plain: bool = False,
    ):
        """Initialize the Inventory Manager."""
        self.role_path = role_path
        self.inventory_path = inventory_path
        self.vault_pw = vault_pw
        self.overrides = overrides
        self.allow_empty_plain = allow_empty_plain
        self.inventory = YamlHandler.load_yaml(inventory_path)
        self.schema = YamlHandler.load_yaml(role_path / "schema" / "main.yml")
        self.app_id = self.load_application_id(role_path)

        self.vault_handler = VaultHandler(vault_pw)
        self.roles_root = self.role_path.parent
        self.value_generator = ValueGenerator()

    def load_application_id(self, role_path: Path) -> str:
        """Load the application ID from the role's vars/main.yml file."""
        vars_file = role_path / "vars" / "main.yml"
        data = YamlHandler.load_yaml(vars_file)
        app_id = data.get("application_id")
        if not app_id:
            print(f"ERROR: 'application_id' missing in {vars_file}", file=sys.stderr)
            sys.exit(1)
        return app_id

    def load_role_schema(self, role_name: str) -> dict:
        schema_path = self.roles_root / role_name / "schema" / "main.yml"
        if not schema_path.exists():
            print(f"ERROR: schema not found: {schema_path}", file=sys.stderr)
            sys.exit(1)
        return YamlHandler.load_yaml(schema_path) or {}

    def resolve_schema_includes(self, config: dict) -> List[str]:
        services = (config.get("docker") or {}).get("services") or {}

        includes: List[str] = []

        ldap = services.get("ldap") or {}
        if ldap.get("enabled") is True and ldap.get("shared") is True:
            includes.append("svc-db-openldap")

        oidc = services.get("oidc") or {}
        if oidc.get("enabled") is True and oidc.get("shared") is True:
            includes.append("web-app-keycloak")

        matomo = services.get("matomo") or {}
        if matomo.get("enabled") is True and matomo.get("shared") is True:
            includes.append("web-app-matomo")

        db = services.get("database") or {}
        if db.get("enabled") is True and db.get("shared") is True:
            db_type = (db.get("type") or "").strip()
            if db_type:
                includes.append(f"svc-db-{db_type}")
            else:
                print(
                    "ERROR: docker.services.database.enabled=true and shared=true but docker.services.database.type is missing",
                    file=sys.stderr,
                )
                sys.exit(1)

        deduped: List[str] = []
        seen = set()
        for r in includes:
            if r not in seen:
                deduped.append(r)
                seen.add(r)
        return deduped

    def apply_schema(self) -> Dict:
        """Apply the schema and return the updated inventory."""
        apps = self.inventory.setdefault("applications", {})

        # Load the data from config/main.yml
        vars_file = self.role_path / "config" / "main.yml"
        data = YamlHandler.load_yaml(vars_file) or {}

        # Apply schemas for shared provider roles into their own application blocks
        for role_name in self.resolve_schema_includes(data):
            provider_role_path = self.roles_root / role_name
            provider_app_id = self.load_application_id(provider_role_path)
            provider_target = apps.setdefault(provider_app_id, {})
            provider_schema = self.load_role_schema(role_name)
            self.recurse_credentials(provider_schema, provider_target)

        # Apply this role's schema into its own application block
        target = apps.setdefault(self.app_id, {})

        services = (data.get("docker") or {}).get("services") or {}

        database = services.get("database") or {}
        oauth2 = services.get("oauth2") or {}

        # docker.services.database.shared
        if database.get("shared") is True:
            target.setdefault("credentials", {})["database_password"] = (
                self.value_generator.generate_value("alphanumeric")
            )

        # docker.services.oauth2.enabled
        if oauth2.get("enabled") is True:
            target.setdefault("credentials", {})["oauth2_proxy_cookie_secret"] = (
                self.value_generator.generate_value("random_hex_16")
            )

        # Apply recursion only for the `credentials` section
        self.recurse_credentials(self.schema, target)
        return self.inventory

    def recurse_credentials(self, branch: dict, dest: dict, prefix: str = ""):
        """Recursively process only the 'credentials' section and generate values."""
        for key, meta in branch.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if (
                prefix == "credentials"
                and isinstance(meta, dict)
                and all(k in meta for k in ("description", "algorithm", "validation"))
            ):
                alg = meta["algorithm"]
                if alg == "plain":
                    if full_key not in self.overrides:
                        if self.allow_empty_plain:
                            plain = ""
                        else:
                            print(
                                f"ERROR: Plain algorithm for '{full_key}' requires override via --set {full_key}=<value>",
                                file=sys.stderr,
                            )
                            sys.exit(1)
                    else:
                        plain = self.overrides[full_key]
                else:
                    plain = self.overrides.get(
                        full_key, self.value_generator.generate_value(alg)
                    )

                existing_value = dest.get(key)

                if isinstance(existing_value, dict):
                    print(
                        f"Skipping encryption for '{key}', as it is a dictionary.",
                        file=sys.stderr,
                    )
                    continue

                if existing_value and isinstance(existing_value, VaultScalar):
                    print(
                        f"Skipping encryption for '{key}', as it is already vaulted.",
                        file=sys.stderr,
                    )
                    continue

                if plain == "":
                    dest[key] = ""
                    continue

                snippet = self.vault_handler.encrypt_string(plain, key)
                lines = snippet.splitlines()
                indent = len(lines[1]) - len(lines[1].lstrip())
                body = "\n".join(line[indent:] for line in lines[1:])
                dest[key] = VaultScalar(body)

            elif isinstance(meta, dict):
                sub = dest.setdefault(key, {})
                self.recurse_credentials(meta, sub, full_key)
            else:
                dest[key] = meta
