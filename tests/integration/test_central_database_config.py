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


class TestCentralDatabaseConfig(unittest.TestCase):
    def test_central_database_feature_requires_database_service(self):
        """
        If docker.services.database.shared is defined in either vars/main.yml or config/main.yml,
        then config/main.yml must define docker.services.database.
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

            # Check if the feature key is defined in either file (value is irrelevant).
            vars_features = (
                vars_data.get("features", {})
                if isinstance(vars_data.get("features"), dict)
                else {}
            )
            cfg_features = (
                cfg_data.get("features", {})
                if isinstance(cfg_data.get("features"), dict)
                else {}
            )
            central_defined = ("central_database" in vars_features) or (
                "central_database" in cfg_features
            )

            if not central_defined:
                continue

            # Require docker.services.database in config/main.yml
            docker = cfg_data.get("docker", {})
            services = docker.get("services", {}) if isinstance(docker, dict) else {}
            if "database" not in services:
                violations.append(role_dir.name)

        if violations:
            self.fail(
                "The 'central_database' feature is only available if 'docker.services.database' "
                "is defined in config/main.yml. Missing in roles:\n"
                + "\n".join(f"- {name}" for name in violations)
            )


if __name__ == "__main__":
    unittest.main()
