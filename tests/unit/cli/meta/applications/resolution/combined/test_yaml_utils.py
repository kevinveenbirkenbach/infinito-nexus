# tests/unit/cli/meta/applications/resolution/combined/test_yaml_utils.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.meta.applications.resolution.combined.errors import CombinedResolutionError
from cli.meta.applications.resolution.combined.yaml_utils import load_yaml_file


class TestYamlUtils(unittest.TestCase):
    def test_load_yaml_file_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.yml"
            p.write_text("a: 1\nb:\n  c: 2\n", encoding="utf-8")
            data = load_yaml_file(p)
            self.assertEqual(data["a"], 1)
            self.assertEqual(data["b"]["c"], 2)

    def test_load_yaml_file_empty_returns_dict(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.yml"
            p.write_text("", encoding="utf-8")
            data = load_yaml_file(p)
            self.assertEqual(data, {})

    def test_load_yaml_file_invalid_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.yml"
            p.write_text("a: [\n", encoding="utf-8")  # invalid YAML
            with self.assertRaises(CombinedResolutionError):
                load_yaml_file(p)
