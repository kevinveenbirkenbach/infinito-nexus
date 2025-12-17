import os
import unittest
import yaml
from collections import defaultdict


class TestPortsUniqueness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(__file__)
        cls.ports_file = os.path.abspath(
            os.path.join(base_dir, "..", "..", "group_vars", "all", "10_ports.yml")
        )
        # Try to load data; leave it as None if missing or invalid YAML
        try:
            with open(cls.ports_file, "r", encoding="utf-8") as f:
                cls.data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            cls.data = None
        except yaml.YAMLError as e:
            raise RuntimeError(f"Failed to parse {cls.ports_file}: {e}")

    def test_ports_file_exists(self):
        """Fail if the ports file is missing."""
        self.assertTrue(
            os.path.isfile(self.ports_file), f"{self.ports_file} does not exist."
        )

    def _collect_ports(self, section):
        """
        Helper to collect a mapping from port -> list of 'category.service' identifiers
        for a given section ('localhost' or 'public').
        """
        ports_section = self.data.get("ports", {}).get(section, {})
        port_map = defaultdict(list)

        for category, services in ports_section.items():
            if not isinstance(services, dict):
                continue
            for service, port in services.items():
                try:
                    port_num = int(port)
                except (TypeError, ValueError):
                    self.fail(
                        f"Invalid port value for {section}.{category}.{service}: {port!r}"
                    )
                identifier = f"{category}.{service}"
                port_map[port_num].append(identifier)
        return port_map

    def _assert_unique(self, port_map, section):
        """
        Assert no port number is assigned more than once in the given section.
        """
        duplicates = {p: svcs for p, svcs in port_map.items() if len(svcs) > 1}
        if duplicates:
            msgs = [
                f"Port {p} is duplicated for services: {', '.join(svcs)}"
                for p, svcs in duplicates.items()
            ]
            self.fail(f"Duplicate {section} ports found:\n" + "\n".join(msgs))

    def test_unique_localhost_ports(self):
        """All localhost‐exposed ports must be unique."""
        # Ensure the file was loaded
        self.assertIsNotNone(
            self.data, f"{self.ports_file} does not exist or is unreadable."
        )
        port_map = self._collect_ports("localhost")
        self._assert_unique(port_map, "localhost")

    def test_unique_public_ports(self):
        """All public‐exposed ports must be unique."""
        # Ensure the file was loaded
        self.assertIsNotNone(
            self.data, f"{self.ports_file} does not exist or is unreadable."
        )
        port_map = self._collect_ports("public")
        self._assert_unique(port_map, "public")


if __name__ == "__main__":
    unittest.main()
