"""Per req-009: subnets declared per-role under
``meta/server.yml.networks.local.subnet`` MUST be valid, unique, and
non-overlapping across the role tree."""

from __future__ import annotations

import glob
import ipaddress
import unittest
from pathlib import Path

import yaml


class TestNetworksUniqueValidAndMapped(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from . import PROJECT_ROOT

        cls.repo_root = str(PROJECT_ROOT)
        cls.roles_dir = str(PROJECT_ROOT / "roles")

        cls.role_to_subnet: dict[str, ipaddress.IPv4Network] = {}
        for role_path in sorted(glob.glob(str(Path(cls.roles_dir) / "*"))):
            if not Path(role_path).is_dir():
                continue
            server_file = str(Path(role_path) / "meta" / "server.yml")
            if not Path(server_file).is_file():
                continue
            with Path(server_file).open(encoding="utf-8") as f:
                server_data = yaml.safe_load(f) or {}
            networks = server_data.get("networks") or {}
            if not isinstance(networks, dict):
                continue
            local = networks.get("local")
            if not isinstance(local, dict):
                continue
            subnet = local.get("subnet")
            if not isinstance(subnet, str):
                continue
            try:
                cls.role_to_subnet[Path(role_path).name] = ipaddress.IPv4Network(
                    subnet.strip()
                )
            except (ValueError, ipaddress.AddressValueError) as exc:
                raise AssertionError(
                    f"Invalid subnet for role '{Path(role_path).name}': "
                    f"{subnet!r} ({exc})"
                ) from exc

    def test_unique_subnets(self):
        seen: dict[ipaddress.IPv4Network, str] = {}
        dupes: list[str] = []
        for role, net in self.role_to_subnet.items():
            if net in seen:
                dupes.append(f"{seen[net]} and {role} both use {net}")
            else:
                seen[net] = role
        if dupes:
            self.fail(
                "Duplicate subnets detected:\n"
                + "\n".join(dupes)
                + "\n\nFix: pick a free subnet via "
                + "`infinito meta networks suggest --clients <N> --count 1` "
                + "and update the role's meta/server.yml.networks.local.subnet."
            )

    def test_no_overlapping_subnets(self):
        items = list(self.role_to_subnet.items())
        overlaps: list[str] = []
        for i in range(len(items)):
            name1, net1 = items[i]
            for j in range(i + 1, len(items)):
                name2, net2 = items[j]
                if net1.overlaps(net2):
                    overlaps.append(f"'{name1}' ({net1}) overlaps '{name2}' ({net2})")
        if overlaps:
            self.fail(
                "Subnet overlaps detected:\n"
                + "\n".join(overlaps)
                + "\n\nFix: pick a free subnet via "
                + "`infinito meta networks suggest --clients <N> --count 1` "
                + "and update the role's meta/server.yml.networks.local.subnet."
            )


if __name__ == "__main__":
    unittest.main()
