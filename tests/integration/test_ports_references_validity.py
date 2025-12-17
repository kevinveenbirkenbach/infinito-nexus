import os
import unittest
import yaml
import re


class TestPortReferencesValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # locate and load the ports definition
        base = os.path.dirname(__file__)
        cls.ports_file = os.path.abspath(
            os.path.join(base, "..", "..", "group_vars", "all", "10_ports.yml")
        )
        if not os.path.isfile(cls.ports_file):
            raise FileNotFoundError(f"{cls.ports_file} does not exist.")

        with open(cls.ports_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # collect all valid (host, category, service) triples
        cls.valid = set()
        for host, cats in data.get("ports", {}).items():
            if not isinstance(cats, dict):
                continue
            for cat, services in cats.items():
                if not isinstance(services, dict):
                    continue
                for svc in services:
                    cls.valid.add((host, cat, svc))

        # prepare regex patterns for the allowed reference forms
        cls.patterns = [
            # dot notation: ports.host.cat.svc
            re.compile(
                r"ports\.(?P<host>localhost|public)\.(?P<cat>[A-Za-z0-9_]+)\.(?P<svc>[A-Za-z0-9_]+)\b"
            ),
            # bracket notation: ports.host.cat['svc'] or ["svc"]
            re.compile(
                r"ports\.(?P<host>localhost|public)\.(?P<cat>[A-Za-z0-9_]+)\[\s*['\"](?P<svc>[A-Za-z0-9_]+)['\"]\s*\]"
            ),
            # get(): ports.host.cat.get('svc')
            re.compile(
                r"ports\.(?P<host>localhost|public)\.(?P<cat>[A-Za-z0-9_]+)\.get\(\s*['\"](?P<svc>[A-Za-z0-9_]+)['\"]\s*\)"
            ),
        ]

    def test_port_references_point_to_defined_ports(self):
        """
        Scan all .j2, .yml, .yaml files under roles/, group_vars/, host_vars/, tasks/,
        templates/, and playbooks/ for any ports.<host>.<category>.<service> references
        (dot, [''], or .get('')) and verify each triple is defined in 10_ports.yml.
        """
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        dirs_to_scan = [
            "roles",
            "group_vars",
            "host_vars",
            "tasks",
            "templates",
            "playbooks",
        ]

        errors = []

        for dirname in dirs_to_scan:
            dirpath = os.path.join(project_root, dirname)
            if not os.path.isdir(dirpath):
                continue

            for root, _, files in os.walk(dirpath):
                for fname in files:
                    if not (fname.endswith((".j2", ".yml", ".yaml"))):
                        continue

                    path = os.path.join(root, fname)
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for lineno, line in enumerate(fh, start=1):
                            for pat in self.patterns:
                                for m in pat.finditer(line):
                                    triple = (
                                        m.group("host"),
                                        m.group("cat"),
                                        m.group("svc"),
                                    )
                                    if triple not in self.valid:
                                        errors.append(
                                            f"{path}:{lineno}: reference `{m.group(0)}` "
                                            f"not found in {self.ports_file}"
                                        )

        if errors:
            self.fail("Found invalid port references:\n" + "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
