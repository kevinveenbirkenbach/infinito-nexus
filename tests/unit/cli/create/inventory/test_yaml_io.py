import tempfile
import unittest
from pathlib import Path

import yaml

from cli.create.inventory.yaml_io import load_yaml, dump_yaml


class TestYamlIO(unittest.TestCase):
    def test_load_yaml_missing_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "missing.yml"
            self.assertEqual(load_yaml(p), {})

    def test_dump_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "a.yml"
            data = {"a": 1, "b": {"c": True}}
            dump_yaml(p, data)
            self.assertEqual(load_yaml(p), data)

    def test_load_yaml_rejects_non_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "bad.yml"
            p.write_text(yaml.safe_dump(["not-a-mapping"]), encoding="utf-8")
            with self.assertRaises(SystemExit):
                load_yaml(p)
