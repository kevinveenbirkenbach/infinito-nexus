import os
import unittest
import yaml
import glob
import ipaddress

class TestNetworksUniqueValidAndMapped(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # locate group_vars/all/09_networks.yml
        base_dir = os.path.dirname(__file__)
        cls.networks_file = os.path.abspath(
            os.path.join(base_dir, '..', '..', 'group_vars', 'all', '09_networks.yml')
        )
        if os.path.isfile(cls.networks_file):
            with open(cls.networks_file, 'r', encoding='utf-8') as f:
                cls.networks_data = yaml.safe_load(f)
        else:
            cls.networks_data = None

    def test_networks_file_exists(self):
        """Fail if the networks file is missing."""
        self.assertTrue(
            os.path.isfile(self.networks_file),
            f"{self.networks_file} does not exist."
        )

    def test_unique_and_non_overlapping_subnets(self):
        """Ensure that all subnets are valid, unique and do not overlap."""
        if self.networks_data is None:
            self.skipTest("09_networks.yml not found, skipping subnet validation.")

        # extract all named subnets under defaults_networks.local
        local = self.networks_data.get('defaults_networks', {}).get('local', {})
        name_to_net = {}
        for name, cfg in local.items():
            subnet = cfg.get('subnet')
            if not subnet:
                continue
            try:
                net = ipaddress.ip_network(subnet)
            except ValueError as e:
                self.fail(f"Invalid subnet for network '{name}': {subnet} ({e})")
            name_to_net[name] = net

        # check for duplicate subnets
        nets = list(name_to_net.values())
        if len(nets) != len(set(nets)):
            seen = {}
            dupes = []
            for nm, net in name_to_net.items():
                if net in seen:
                    dupes.append(f"{seen[net]} and {nm} both use {net}")
                else:
                    seen[net] = nm
            self.fail("Duplicate subnets detected:\n" + "\n".join(dupes))

        # check for overlaps
        items = list(name_to_net.items())
        for i in range(len(items)):
            name1, net1 = items[i]
            for j in range(i+1, len(items)):
                name2, net2 = items[j]
                if net1.overlaps(net2):
                    self.fail(
                        f"Subnet overlap between '{name1}' ({net1}) and "
                        f"'{name2}' ({net2})."
                    )

    def test_network_names_mapped_to_application_id(self):
        """
        Ensure each network name with a subnet under defaults_networks.local
        matches an application_id in some roles/*/vars/main.yml.
        """
        if self.networks_data is None:
            self.skipTest("09_networks.yml not found, skipping application_id mapping check.")

        # collect network names
        local = self.networks_data.get('defaults_networks', {}).get('local', {})
        network_names = [name for name, cfg in local.items() if 'subnet' in cfg]

        # gather all application_id values from roles/*/vars/main.yml
        base_dir = os.path.dirname(__file__)
        roles_dir = os.path.abspath(os.path.join(base_dir, '..', '..', 'roles'))
        app_ids = set()
        for role_path in glob.glob(os.path.join(roles_dir, '*')):
            vars_file = os.path.join(role_path, 'vars', 'main.yml')
            if not os.path.isfile(vars_file):
                continue
            with open(vars_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            app_id = data.get('application_id')
            if app_id:
                app_ids.add(app_id)

        missing = [nm for nm in network_names if nm not in app_ids]
        if missing:
            self.fail(
                "The following networks have no matching application_id in any role:\n"
                + ", ".join(missing)
            )

if __name__ == '__main__':
    unittest.main()
