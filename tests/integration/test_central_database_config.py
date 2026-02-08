# tests/integration/test_central_database_config.py
import unittest
from pathlib import Path
import yaml


def load_yaml(path: Path):
    """Load a YAML file and return dict ({} if missing/empty)."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def has_nested_key(data: object, dotted_key: str) -> bool:
    """
    Return True if a dotted path exists in a nested dict structure.
    Example: has_nested_key(cfg, "compose.services.database.shared")
    """
    if not isinstance(data, dict):
        return False

    cur: object = data
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return False
        if part not in cur:
            return False
        cur = cur[part]
    return True


class TestCentralDatabaseConfig(unittest.TestCase):
    def test_central_database_feature_requires_database_service(self):
        """
        If compose.services.database.shared is defined in either vars/main.yml or config/main.yml,
        then config/main.yml must define compose.services.database.
        """
        repo_root = Path(__file__).resolve().parents[2]
        roles_dir = repo_root / "roles"

        violations = []

        for role_dir in sorted(roles_dir.glob("*")):
            if not role_dir.is_dir():
                continue

            vars_file = role_dir / "vars" / "main.yml"
            cfg_file = role_dir / "config" / "main.yml"

            vars_data = load_yaml(vars_file)
            cfg_data = load_yaml(cfg_file)

            # Trigger: compose.services.database.shared defined in either file (value irrelevant)
            shared_defined = has_nested_key(
                vars_data, "compose.services.database.shared"
            ) or has_nested_key(cfg_data, "compose.services.database.shared")
            if not shared_defined:
                continue

            # Requirement: compose.services.database must be defined in config/main.yml
            if not has_nested_key(cfg_data, "compose.services.database"):
                violations.append(role_dir.name)

        if violations:
            self.fail(
                "The 'compose.services.database.shared' flag is only valid if 'compose.services.database' "
                "is defined in config/main.yml. Missing in roles:\n"
                + "\n".join(f"- {name}" for name in violations)
            )


if __name__ == "__main__":
    unittest.main()
