import unittest
import ipaddress
import os
import shutil
import tempfile
from ruamel.yaml import YAML

# Import functions to test; adjust path as needed
from cli.create.role import (
    get_next_network,
    get_next_port,
    load_yaml_with_comments,
    dump_yaml_with_comments,
    render_templates,
)


class TestCreateDockerRoleCLI(unittest.TestCase):
    def setUp(self):
        # Temporary directory for YAML files and templates
        self.tmpdir = tempfile.mkdtemp()
        self.ports_file = os.path.join(self.tmpdir, "11_ports.yml")
        self.networks_file = os.path.join(self.tmpdir, "10_networks.yml")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_get_next_network_multiple(self):
        networks = {
            "defaults_networks": {
                "local": {
                    "app1": {"subnet": "192.168.0.0/28"},
                    "app2": {"subnet": "192.168.0.16/28"},
                }
            }
        }
        next_net = get_next_network(networks, 28)
        self.assertEqual(next_net, ipaddress.ip_network("192.168.0.32/28"))

    def test_get_next_network_single(self):
        networks = {
            "defaults_networks": {
                "local": {
                    "only": {"subnet": "10.0.0.0/24"},
                }
            }
        }
        next_net = get_next_network(networks, 24)
        self.assertEqual(next_net, ipaddress.ip_network("10.0.1.0/24"))

    def test_get_next_port_existing(self):
        ports = {"ports": {"localhost": {"http": {"app1": "8000", "app2": "8001"}}}}
        next_port = get_next_port(ports, "http")
        self.assertEqual(next_port, 8002)

    def test_get_next_port_empty(self):
        ports = {"ports": {"localhost": {"ldap": {}}}}
        next_port = get_next_port(ports, "ldap")
        self.assertEqual(next_port, 1)

    def test_yaml_load_dump_preserves_comments(self):
        # Initialize ruamel.yaml
        yaml = YAML()
        yaml.preserve_quotes = True
        # Create sample file with comment
        content = (
            "# Ports file\n"
            "ports:\n"
            "  localhost:\n"
            "    http:\n"
            "      app1: 8000  # existing port\n"
        )
        with open(self.ports_file, "w") as f:
            f.write(content)
        # Load and modify
        data = load_yaml_with_comments(self.ports_file)
        data["ports"]["localhost"]["http"]["app2"] = 8001
        dump_yaml_with_comments(data, self.ports_file)
        # Check comment and new entry
        with open(self.ports_file) as f:
            text = f.read()
        self.assertIn("# existing port", text)
        self.assertIn("app2: 8001", text)

    def test_render_creates_and_overwrites_skips_merges(self):
        # Prepare source and dest directories
        src = os.path.join(self.tmpdir, "src")
        dst = os.path.join(self.tmpdir, "dst")
        os.makedirs(src)
        os.makedirs(dst)
        # Template file
        tpl = os.path.join(src, "file.txt.j2")
        with open(tpl, "w") as f:
            f.write("Line1\nLine2")
        out_file = os.path.join(dst, "file.txt")
        # Test create
        render_templates(src, dst, {})
        with open(out_file) as f:
            self.assertEqual(f.read(), "Line1\nLine2")
        # Test overwrite
        with open(out_file, "w") as f:
            f.write("Old")
        import builtins

        original_input = builtins.input
        builtins.input = lambda _: "1"
        render_templates(src, dst, {})
        with open(out_file) as f:
            self.assertEqual(f.read(), "Line1\nLine2")
        # Test skip
        with open(out_file, "w") as f:
            f.write("Old")
        builtins.input = lambda _: "2"
        render_templates(src, dst, {})
        with open(out_file) as f:
            self.assertEqual(f.read(), "Old")
        # Test merge
        with open(out_file, "w") as f:
            f.write("Line1\n")
        builtins.input = lambda _: "3"
        render_templates(src, dst, {})
        with open(out_file) as f:
            content = f.read().splitlines()
        self.assertIn("Line1", content)
        self.assertIn("Line2", content)
        builtins.input = original_input


if __name__ == "__main__":
    unittest.main()
