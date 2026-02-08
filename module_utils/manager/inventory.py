from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set

from module_utils.handler.yaml import YamlHandler
from module_utils.handler.vault import VaultHandler, VaultScalar
from module_utils.manager.value_generator import ValueGenerator


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

        self.inventory = YamlHandler.load_yaml(inventory_path) or {}
        schema_file = role_path / "schema" / "main.yml"
        self.schema = YamlHandler.load_yaml(schema_file) if schema_file.exists() else {}
        self.app_id = self.load_application_id(role_path)

        self.vault_handler = VaultHandler(vault_pw)
        self.roles_root = self.role_path.parent
        self.value_generator = ValueGenerator()

    # ---------------------------------------------------------------------
    # File loading helpers
    # ---------------------------------------------------------------------

    def load_application_id(self, role_path: Path) -> str:
        """Load the application ID from the role's vars/main.yml file."""
        vars_file = role_path / "vars" / "main.yml"
        data = YamlHandler.load_yaml(vars_file) or {}
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

    def load_role_config_by_path(self, role_path: Path) -> dict:
        cfg_path = role_path / "config" / "main.yml"
        if not cfg_path.exists():
            return {}
        return YamlHandler.load_yaml(cfg_path) or {}

    def load_role_config(self, role_name: str) -> dict:
        role_path = self.roles_root / role_name
        return self.load_role_config_by_path(role_path)

    # ---------------------------------------------------------------------
    # Shared provider resolution (recursive / transitive)
    # ---------------------------------------------------------------------

    def _direct_schema_includes_from_config(self, config: dict) -> List[str]:
        """
        Extract shared-provider dependencies from a single role config.
        """
        services = (config.get("compose") or {}).get("services") or {}
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
            if not db_type:
                print(
                    "ERROR: compose.services.database.enabled=true and shared=true but compose.services.database.type is missing",
                    file=sys.stderr,
                )
                sys.exit(1)
            includes.append(f"svc-db-{db_type}")

        # stable order, dedup
        out: List[str] = []
        seen: Set[str] = set()
        for r in includes:
            if r not in seen:
                out.append(r)
                seen.add(r)
        return out

    def resolve_schema_includes_recursive(self, root_role_name: str) -> List[str]:
        """
        Recursively resolve schema includes by following configs transitively.
        """
        resolved: List[str] = []
        seen: Set[str] = set()

        # seed with root role's direct includes
        root_cfg = self.load_role_config_by_path(self.role_path)
        queue: List[str] = self._direct_schema_includes_from_config(root_cfg)

        while queue:
            role_name = queue.pop(0)
            if role_name in seen:
                continue
            seen.add(role_name)
            resolved.append(role_name)

            cfg = self.load_role_config(role_name)
            for inc in self._direct_schema_includes_from_config(cfg):
                if inc not in seen:
                    queue.append(inc)

        return resolved

    # ---------------------------------------------------------------------
    # Schema application
    # ---------------------------------------------------------------------

    def _apply_one_role_schema(self, role_name: str) -> None:
        """
        Apply schema for a specific role into its application block.
        """
        role_path = self.roles_root / role_name
        app_id = self.load_application_id(role_path)
        schema = self.load_role_schema(role_name)

        apps = self.inventory.setdefault("applications", {})
        target = apps.setdefault(app_id, {})

        self.recurse_credentials(schema, target)

    def _apply_one_role_special_rules(self, role_path: Path) -> None:
        """
        Apply special credential rules based on role config flags.
        """
        app_id = self.load_application_id(role_path)
        cfg = self.load_role_config_by_path(role_path)

        apps = self.inventory.setdefault("applications", {})
        target = apps.setdefault(app_id, {})

        services = (cfg.get("compose") or {}).get("services") or {}
        database = services.get("database") or {}
        oauth2 = services.get("oauth2") or {}

        if database.get("enabled") is True and database.get("shared") is True:
            target.setdefault("credentials", {})["database_password"] = (
                self.value_generator.generate_value("alphanumeric")
            )

        if oauth2.get("enabled") is True:
            target.setdefault("credentials", {})["oauth2_proxy_cookie_secret"] = (
                self.value_generator.generate_value("random_hex_16")
            )

    def apply_schema(self) -> Dict:
        """
        Apply schema into inventory for:
          1) all recursively discovered shared-provider roles
          2) this role itself
        """
        # 1) Provider roles (transitive)
        for role_name in self.resolve_schema_includes_recursive(self.role_path.name):
            role_path = self.roles_root / role_name
            self._apply_one_role_special_rules(role_path)
            self._apply_one_role_schema(role_name)

        # 2) Root role
        self._apply_one_role_special_rules(self.role_path)

        apps = self.inventory.setdefault("applications", {})
        target = apps.setdefault(self.app_id, {})
        self.recurse_credentials(self.schema, target)

        return self.inventory

    # ---------------------------------------------------------------------
    # Credential recursion
    # ---------------------------------------------------------------------

    def recurse_credentials(self, branch: dict, dest: dict, prefix: str = "") -> None:
        """Recursively process only the 'credentials' section and generate values."""
        for key, meta in (branch or {}).items():
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
