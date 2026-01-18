# module_utils/manager/value_generator.py

import secrets
import hashlib
import bcrypt
import string
import base64


class ValueGenerator:
    def generate_strong_password(self, length: int = 32) -> str:
        characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}:,.?"
        return "".join(secrets.choice(characters) for _ in range(length))

    def generate_secure_alphanumeric(self, length: int) -> str:
        """Generate a cryptographically secure random alphanumeric string of the given length."""
        characters = string.ascii_letters + string.digits  # a-zA-Z0-9
        return "".join(secrets.choice(characters) for _ in range(length))

    def generate_value(self, algorithm: str) -> str:
        """
        Generate a random secret value according to the specified algorithm.

        Supported algorithms:
        • "random_hex"
        • "random_hex_32"
        • "random_hex_16"
        • "sha256"
        • "sha1"
        • "bcrypt"
        • "alphanumeric"
        • "base64_prefixed_32"
        """
        if algorithm == "random_hex":
            return secrets.token_hex(64)
        if algorithm == "random_hex_32":
            return secrets.token_hex(32)
        if algorithm == "random_hex_16":
            return secrets.token_hex(16)
        if algorithm == "sha256":
            return hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        if algorithm == "sha1":
            return hashlib.sha1(secrets.token_bytes(20)).hexdigest()
        if algorithm == "strong_password":
            return self.generate_strong_password(32)
        if algorithm == "bcrypt":
            pw = secrets.token_urlsafe(16).encode()
            raw_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
            alnum = string.digits + string.ascii_lowercase
            escaped = "".join(
                secrets.choice(alnum) if ch == "$" else ch for ch in raw_hash
            )
            return escaped
        if algorithm == "alphanumeric":
            return self.generate_secure_alphanumeric(64)
        if algorithm == "base64_prefixed_32":
            return "base64:" + base64.b64encode(secrets.token_bytes(32)).decode()
        return "undefined"
