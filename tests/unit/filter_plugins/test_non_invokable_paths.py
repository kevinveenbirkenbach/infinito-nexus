import unittest
import tempfile
import yaml
import os

from filter_plugins.invokable_paths import get_non_invokable_paths


class TestNonInvokablePaths(unittest.TestCase):
    def write_yaml(self, data):
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yml")
        yaml.dump(data, tmp)
        tmp.close()
        return tmp.name

    def test_empty_roles(self):
        path = self.write_yaml({})
        # No roles, so no non-invokable paths
        self.assertEqual(get_non_invokable_paths(path), [])
        os.unlink(path)

    def test_single_non_invokable_false_and_missing(self):
        data_false = {"role1": {"invokable": False}}
        path_false = self.write_yaml(data_false)
        self.assertEqual(get_non_invokable_paths(path_false), ["role1"])
        os.unlink(path_false)

        data_missing = {"role1": {}}
        path_missing = self.write_yaml(data_missing)
        self.assertEqual(get_non_invokable_paths(path_missing), ["role1"])
        os.unlink(path_missing)

    def test_single_invokable_true_excluded(self):
        data = {"role1": {"invokable": True}}
        path = self.write_yaml(data)
        # invokable True should not appear in non-invokable list
        self.assertEqual(get_non_invokable_paths(path), [])
        os.unlink(path)

    def test_nested_and_deeply_nested(self):
        data = {
            "parent": {
                "invokable": True,
                "child": {"invokable": False},
                "other": {"invokable": True},
                "sub": {"deep": {}},
            }
        }
        path = self.write_yaml(data)
        # 'parent-child' (explicit False), 'parent-sub' (missing invokable), and 'parent-sub-deep' (missing) are non-invokable
        expected = ["parent-child", "parent-sub", "parent-sub-deep"]
        self.assertEqual(sorted(get_non_invokable_paths(path)), sorted(expected))
        os.unlink(path)

    def test_unwrap_roles_key(self):
        data = {"roles": {"role1": {"invokable": False}, "role2": {"invokable": True}}}
        path = self.write_yaml(data)
        # Only role1 is non-invokable
        self.assertEqual(get_non_invokable_paths(path), ["role1"])
        os.unlink(path)

    def test_suffix_appended(self):
        data = {"role1": {"invokable": False}}
        path = self.write_yaml(data)
        self.assertEqual(get_non_invokable_paths(path, suffix="_suf"), ["role1_suf"])
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
