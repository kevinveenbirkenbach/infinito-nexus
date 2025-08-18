import unittest
import os
import sys

# Add the path to roles/sys-ctl-bkp-docker-2-loc/filter_plugins
CURRENT_DIR = os.path.dirname(__file__)
FILTER_PLUGIN_DIR = os.path.abspath(
    os.path.join(CURRENT_DIR, '../../../../../roles/sys-ctl-bkp-docker-2-loc/filter_plugins')
)
sys.path.insert(0, FILTER_PLUGIN_DIR)

from dict_to_cli_args import dict_to_cli_args


class TestDictToCliArgs(unittest.TestCase):
    def test_simple_string_args(self):
        data = {"backup-dir": "/mnt/backups", "version-suffix": "-nightly"}
        expected = "--backup-dir=/mnt/backups --version-suffix=-nightly"
        self.assertEqual(dict_to_cli_args(data), expected)

    def test_boolean_true(self):
        data = {"shutdown": True, "everything": True}
        expected = "--shutdown --everything"
        self.assertEqual(dict_to_cli_args(data), expected)

    def test_boolean_false(self):
        data = {"shutdown": False, "everything": True}
        expected = "--everything"
        self.assertEqual(dict_to_cli_args(data), expected)

    def test_list_argument(self):
        data = {"ignore-volumes": ["redis", "memcached"]}
        expected = '--ignore-volumes="redis memcached"'
        self.assertEqual(dict_to_cli_args(data), expected)

    def test_mixed_arguments(self):
        data = {
            "backup-dir": "/mnt/backups",
            "shutdown": True,
            "ignore-volumes": ["redis", "memcached"]
        }
        result = dict_to_cli_args(data)
        self.assertIn("--backup-dir=/mnt/backups", result)
        self.assertIn("--shutdown", result)
        self.assertIn('--ignore-volumes="redis memcached"', result)

    def test_empty_dict(self):
        self.assertEqual(dict_to_cli_args({}), "")

    def test_none_value(self):
        data = {"some-value": None, "other": "yes"}
        expected = "--other=yes"
        self.assertEqual(dict_to_cli_args(data), expected)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            dict_to_cli_args(["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()
