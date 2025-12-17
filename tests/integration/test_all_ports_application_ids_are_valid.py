#!/usr/bin/env python3

import os
import unittest
import yaml

from filter_plugins.get_all_application_ids import get_all_application_ids


class TestApplicationIDsInPorts(unittest.TestCase):
    def test_all_ports_application_ids_are_valid(self):
        # Path to the ports definition file
        ports_file = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "group_vars",
                "all",
                "10_ports.yml",
            )
        )
        with open(ports_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Collect all referenced application IDs under ports.hosttype.porttype
        refs = set()
        ports = data.get("ports", {}) or {}
        for hosttype, porttypes in ports.items():
            if not isinstance(porttypes, dict):
                continue
            for porttype, apps in porttypes.items():
                if not isinstance(apps, dict):
                    continue
                for app_id in apps.keys():
                    refs.add(app_id)

        # Retrieve valid application IDs from Ansible roles
        valid_ids = set(get_all_application_ids())

        # Identify IDs that are neither valid nor have a valid prefix before the first underscore
        missing = []
        for app_id in refs:
            if app_id in valid_ids:
                continue
            prefix = app_id.split("_", 1)[0]
            if prefix in valid_ids:
                continue
            missing.append(app_id)

        if missing:
            self.fail(
                f"Undefined application IDs in ports definition: {', '.join(sorted(missing))}"
            )


if __name__ == "__main__":
    unittest.main()
