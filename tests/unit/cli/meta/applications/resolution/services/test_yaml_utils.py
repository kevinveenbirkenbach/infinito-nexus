# tests/unit/cli/meta/applications/resolution/services/test_yaml_utils.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.meta.applications.resolution.services.errors import ServicesResolutionError
from cli.meta.applications.resolution.services.yaml_utils import load_yaml_file


class TestServicesYamlUtils(unittest.TestCase):
    def test_load_yaml_file_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.yml"
            p.write_text("a: 1\n", encoding="utf-8")
            self.assertEqual(load_yaml_file(p)["a"], 1)

    def test_load_yaml_file_invalid_yaml_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.yml"
            p.write_text("a: [1, 2\n", encoding="utf-8")
            with self.assertRaises(ServicesResolutionError):
                load_yaml_file(p)


if __name__ == "__main__":
    unittest.main()
