import unittest
from pathlib import Path

import yaml


def parse_version(version):
    return tuple(int(part) for part in version.lstrip("v").split("."))


class TestShopwareBuildConfiguration(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.role_root = self.repo_root / "roles" / "web-app-shopware"

    def test_shopware_package_version_uses_patched_release(self):
        config_path = self.role_root / "config" / "main.yml"
        config = yaml.safe_load(config_path.read_text("utf-8")) or {}
        version = config["compose"]["services"]["shopware"]["package"]["version"]

        self.assertGreaterEqual(
            parse_version(version),
            (6, 7, 8, 1),
            "Shopware 6.7 releases below 6.7.8.1 are blocked by security advisories.",
        )

    def test_builder_pins_composer_platform_php_to_runtime_series(self):
        vars_path = self.role_root / "vars" / "main.yml"
        dockerfile_path = self.role_root / "templates" / "Dockerfile.j2"

        vars_config = yaml.safe_load(vars_path.read_text("utf-8")) or {}
        dockerfile = dockerfile_path.read_text("utf-8")

        self.assertIn("SHOPWARE_COMPOSER_PLATFORM_PHP", vars_config)
        self.assertIn(
            'composer config platform.php "{{ SHOPWARE_COMPOSER_PLATFORM_PHP }}"',
            dockerfile,
        )


if __name__ == "__main__":
    unittest.main()
