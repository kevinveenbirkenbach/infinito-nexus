import secrets
import hashlib
import bcrypt
from pathlib import Path
from typing import Dict, Any, List
from module_utils.handler.yaml import YamlHandler
from module_utils.handler.vault import VaultHandler, VaultScalar
import string
import sys
import base64


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
        if db.get("shared") is True:
            db_type = (db.get("type") or "").strip()
            if db_type:
                includes.append(f"svc-db-{db_type}")
            else:
                print(
                    "ERROR: docker.services.database.shared=true but docker.services.database.type is missing",
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
                self.generate_value("alphanumeric")
            )

        # docker.services.oauth2.enabled
        if oauth2.get("enabled") is True:
            target.setdefault("credentials", {})["oauth2_proxy_cookie_secret"] = (
                self.generate_value("random_hex_16")
            )

        # Apply recursion only for the `credentials` section
        self.recurse_credentials(self.schema, target)
        return self.inventory

    def recurse_credentials(self, branch: dict, dest: dict, prefix: str = ""):
        """Recursively process only the 'credentials' section and generate values."""
        for key, meta in branch.items():
            full_key = f"{prefix}.{key}" if prefix else key

            # Only process 'credentials' section for encryption
            if (
                prefix == "credentials"
                and isinstance(meta, dict)
                and all(k in meta for k in ("description", "algorithm", "validation"))
            ):
                alg = meta["algorithm"]
                if alg == "plain":
                    # Must be supplied via --set, unless allow_empty_plain=True
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
                    plain = self.overrides.get(full_key, self.generate_value(alg))

                # Check if the value is already vaulted or if it's a dictionary
                existing_value = dest.get(key)

                # If existing_value is a dictionary, print a warning and skip encryption
                if isinstance(existing_value, dict):
                    print(
                        f"Skipping encryption for '{key}', as it is a dictionary.",
                        file=sys.stderr,
                    )
                    continue

                # Check if the value is a VaultScalar and already vaulted
                if existing_value and isinstance(existing_value, VaultScalar):
                    print(
                        f"Skipping encryption for '{key}', as it is already vaulted.",
                        file=sys.stderr,
                    )
                    continue

                # Empty strings should *not* be encrypted
                if plain == "":
                    dest[key] = ""
                    continue

                # Encrypt only if it's not already vaulted
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

    def generate_secure_alphanumeric(self, length: int) -> str:
        """Generate a cryptographically secure random alphanumeric string of the given length."""
        characters = string.ascii_letters + string.digits  # a-zA-Z0-9
        return "".join(secrets.choice(characters) for _ in range(length))

    def generate_value(self, algorithm: str) -> str:
        """
        Generate a random secret value according to the specified algorithm.

        Supported algorithms:
        • "random_hex"
            – Returns a 64-byte (512-bit) secure random string, encoded as 128 hexadecimal characters.
            – Use when you need maximum entropy in a hex-only format.

        • "sha256"
            – Generates 32 random bytes, hashes them with SHA-256, and returns a 64-character hex digest.
            – Good for when you want a fixed-length (256-bit) hash output.

        • "sha1"
            – Generates 20 random bytes, hashes them with SHA-1, and returns a 40-character hex digest.
            – Only use in legacy contexts; SHA-1 is considered weaker than SHA-256.

        • "bcrypt"
            – Creates a random 16-byte URL-safe password, then applies a bcrypt hash.
            – Suitable for storing user-style passwords where bcrypt verification is needed.

        • "alphanumeric"
            – Produces a 64-character string drawn from [A–Z, a–z, 0–9].
            – Offers ≈380 bits of entropy; human-friendly charset.

        • "base64_prefixed_32"
            – Generates 32 random bytes, encodes them in Base64, and prefixes the result with "base64:".
            – Useful when downstream systems expect a Base64 format.

        • "random_hex_16"
            – Returns 16 random bytes (128 bits) encoded as 32 hexadecimal characters.
            – Handy for shorter tokens or salts.

        Returns:
            A securely generated string according to the chosen algorithm.
        """
        if algorithm == "random_hex":
            return secrets.token_hex(64)
        if algorithm == "random_hex_32":
            return secrets.token_hex(32)
        if algorithm == "sha256":
            return hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        if algorithm == "sha1":
            return hashlib.sha1(secrets.token_bytes(20)).hexdigest()
        if algorithm == "bcrypt":
            # Generate a random password and hash it with bcrypt
            pw = secrets.token_urlsafe(16).encode()
            raw_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
            # Replace every '$' with a random lowercase alphanumeric character
            alnum = string.digits + string.ascii_lowercase
            escaped = "".join(
                secrets.choice(alnum) if ch == "$" else ch for ch in raw_hash
            )
            return escaped
        if algorithm == "alphanumeric":
            return self.generate_secure_alphanumeric(64)
        if algorithm == "base64_prefixed_32":
            return "base64:" + base64.b64encode(secrets.token_bytes(32)).decode()
        if algorithm == "random_hex_16":
            # 16 Bytes → 32 Hex-Characters
            return secrets.token_hex(16)
        return "undefined"
