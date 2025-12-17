import unittest
import tempfile
import yaml
import os
from filter_plugins.invokable_paths import get_invokable_paths


class TestInvokablePaths(unittest.TestCase):
    def write_yaml(self, data):
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yml")
        yaml.dump(data, tmp)
        tmp.close()
        return tmp.name

    def test_empty_roles(self):
        path = self.write_yaml({})
        self.assertEqual(get_invokable_paths(path), [])
        os.unlink(path)

    def test_single_invokable_true(self):
        data = {"role1": {"invokable": True}}
        path = self.write_yaml(data)
        self.assertEqual(get_invokable_paths(path), ["role1"])
        os.unlink(path)

    def test_single_invokable_false_or_missing(self):
        data_false = {"role1": {"invokable": False}}
        path_false = self.write_yaml(data_false)
        self.assertEqual(get_invokable_paths(path_false), [])
        os.unlink(path_false)

        data_missing = {"role1": {}}
        path_missing = self.write_yaml(data_missing)
        self.assertEqual(get_invokable_paths(path_missing), [])
        os.unlink(path_missing)

    def test_nested_and_deeply_nested(self):
        data = {
            "parent": {
                "invokable": True,
                "child": {"invokable": True},
                "other": {"invokable": False},
                "sub": {"deep": {"invokable": True}},
            }
        }
        path = self.write_yaml(data)
        expected = ["parent", "parent-child", "parent-sub-deep"]
        self.assertEqual(sorted(get_invokable_paths(path)), sorted(expected))
        os.unlink(path)

    def test_ignore_metadata_and_unwrap(self):
        data = {
            "roles": {
                "role1": {
                    "invokable": True,
                    "title": {"foo": "bar"},
                    "description": {"bar": "baz"},
                }
            }
        }
        path = self.write_yaml(data)
        self.assertEqual(get_invokable_paths(path), ["role1"])
        os.unlink(path)

    def test_suffix_appended(self):
        data = {"role1": {"invokable": True}}
        path = self.write_yaml(data)
        self.assertEqual(get_invokable_paths(path, suffix="_suf"), ["role1_suf"])
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
