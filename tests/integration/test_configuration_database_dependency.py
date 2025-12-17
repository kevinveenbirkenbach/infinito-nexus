import unittest
from pathlib import Path
import yaml


class TestConfigurationDatabaseDependency(unittest.TestCase):
    # Define project root and glob pattern for configuration files
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    CONFIG_PATTERN = "roles/*/config/main.yml"

    def test_central_database_implies_database_service_enabled(self):
        """
        For each roles/*/config/main.yml:
        If features.central_database is true,
        then docker.services.database.enabled must be true.
        """
        config_paths = sorted(self.PROJECT_ROOT.glob(self.CONFIG_PATTERN))
        self.assertTrue(
            config_paths,
            f"No configuration files found for pattern {self.CONFIG_PATTERN}",
        )

        for config_path in config_paths:
            with self.subTest(configuration=config_path):
                content = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

                # Read central_database flag
                features = content.get("features", {})
                central_db = features.get("central_database", False)

                # Read database enabled flag
                docker = content.get("docker", {})
                services = docker.get("services", {})
                database = services.get("database", {})
                db_enabled = database.get("enabled", False)

                if central_db:
                    self.assertTrue(
                        db_enabled,
                        f"{config_path}: features.central_database is true but docker.services.database.enabled is not true",
                    )
                else:
                    # No requirement when central_database is false or absent
                    self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
