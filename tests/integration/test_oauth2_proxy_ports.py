import unittest
import yaml
from pathlib import Path


class TestOAuth2ProxyPorts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up root paths and load oauth2_proxy ports mapping
        cls.ROOT = Path(__file__).parent.parent.parent.resolve()
        cls.PORTS_FILE = cls.ROOT / 'group_vars' / 'all' / '10_ports.yml'
        with cls.PORTS_FILE.open() as f:
            data = yaml.safe_load(f)
        cls.oauth2_ports = (
            data.get('ports', {})
                .get('localhost', {})
                .get('oauth2_proxy', {})
        )

    def test_oauth2_feature_has_port_mapping(self):
        # Iterate over each role directory
        roles_dir = self.ROOT / 'roles'
        for role_path in roles_dir.iterdir():
            if not role_path.is_dir():
                continue
            with self.subTest(role=role_path.name):
                # Check for config/main.yml
                config_file = role_path / "config" / "main.yml"
                if not config_file.exists():
                    self.skipTest(f"No config/main.yml for role {role_path.name}")

                config = yaml.safe_load(config_file.read_text()) or {}
                if not config.get('features', {}).get('oauth2', False):
                    self.skipTest(f"OAuth2 not enabled for role {role_path.name}")

                # Load application_id from vars/main.yml
                main_file = role_path / 'vars' / 'main.yml'
                if not main_file.exists():
                    self.fail(f"Missing vars/main.yml in role {role_path.name}")
                main = yaml.safe_load(main_file.read_text()) or {}
                app_id = main.get('application_id')
                if not app_id:
                    self.fail(f"application_id not set in {main_file}")

                # Validate oauth2_ports structure
                self.assertIsInstance(self.oauth2_ports, dict, 
                                      "oauth2_proxy ports mapping is not a dict")

                # Assert port mapping exists for the application
                if app_id not in self.oauth2_ports:
                    self.fail(
                        f"Missing oauth2_proxy port mapping for application '{app_id}' "
                        f"in group_vars/all/10_ports.yml"
                    )


if __name__ == '__main__':
    unittest.main()
