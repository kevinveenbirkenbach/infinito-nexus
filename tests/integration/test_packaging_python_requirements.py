#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


class TestPackagingPythonRequirements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.arch_pkgbuild = cls.repo_root / "packaging" / "arch" / "PKGBUILD"
        cls.fedora_spec = cls.repo_root / "packaging" / "fedora" / "infinito-nexus.spec"
        cls.debian_control = cls.repo_root / "packaging" / "debian" / "control"

    def test_fedora_spec_relaxes_python_capability_on_el9_only(self):
        spec_text = self.fedora_spec.read_text(encoding="utf-8")
        self.assertRegex(
            spec_text,
            re.compile(
                r"%if 0%\{\?rhel\} == 9\s+"
                r"Requires:\s+python3\s+"
                r"%else\s+"
                r"Requires:\s+python3 >= 3\.11\s+"
                r"%endif",
                re.MULTILINE,
            ),
        )

    def test_debian_control_keeps_explicit_python_311_floor(self):
        control_text = self.debian_control.read_text(encoding="utf-8")
        self.assertIn(" python3 (>= 3.11),", control_text)

    def test_arch_pkgbuild_requires_docker_compose(self):
        pkgbuild_text = self.arch_pkgbuild.read_text(encoding="utf-8")
        self.assertIn("  'docker-compose'", pkgbuild_text)

    def test_debian_control_requires_compose_v2_plugin(self):
        control_text = self.debian_control.read_text(encoding="utf-8")
        self.assertIn(
            " docker-compose-v2 | docker-compose-plugin,",
            control_text,
        )
        self.assertNotIn(
            " docker-compose-v2 | docker-compose-plugin | docker-compose,",
            control_text,
        )

    def test_fedora_spec_requires_compose_plugin(self):
        spec_text = self.fedora_spec.read_text(encoding="utf-8")
        self.assertIn("Requires:       docker-compose-plugin", spec_text)


if __name__ == "__main__":
    unittest.main()
