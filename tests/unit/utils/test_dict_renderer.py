import unittest
from module_utils.dict_renderer import DictRenderer


class TestDictRenderer(unittest.TestCase):
    def setUp(self):
        # Timeout is small for tests, verbose off
        self.renderer = DictRenderer(verbose=False, timeout=1.0)

    def test_simple_replacement(self):
        data = {"foo": "bar", "val": "<<foo>>"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["val"], "bar")

    def test_nested_replacement(self):
        data = {"parent": {"child": "value"}, "ref": "<<parent.child>>"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["ref"], "value")

    def test_list_index(self):
        data = {"lst": [10, 20, 30], "second": "<<lst[1]>>"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["second"], "20")

    def test_multi_pass(self):
        data = {"a": "<<b>>", "b": "<<c>>", "c": "final"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["a"], "final")

    def test_unresolved_raises(self):
        data = {"a": "<<missing>>"}
        with self.assertRaises(ValueError) as cm:
            self.renderer.render(data)
        self.assertIn("missing", str(cm.exception))

    def test_leave_curly(self):
        data = {"tmpl": "{{ not touched }}"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["tmpl"], "{{ not touched }}")

    def test_mixed_braces(self):
        data = {"foo": "bar", "tmpl": "{{ <<foo>> }}"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["tmpl"], "{{ bar }}")

    def test_single_quoted_key(self):
        # ['foo-bar'] should resolve the key 'foo-bar'
        data = {"foo-bar": {"val": "xyz"}, "result": "<<['foo-bar'].val>>"}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["result"], "xyz")

    def test_double_quoted_key(self):
        # ["foo-bar"] should also resolve the key 'foo-bar'
        data = {"foo-bar": {"val": 123}, "result": '<<["foo-bar"].val>>'}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["result"], "123")

    def test_mixed_bracket_and_dot_with_index(self):
        # Combine quoted key, dot access and numeric index
        data = {
            "web-svc-file": {
                "server": {"domains": {"canonical": ["file.example.com"]}}
            },
            "url": "<<['web-svc-file'].server.domains.canonical[0]>>",
        }
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["url"], "file.example.com")

    def test_double_quoted_key_with_list_index(self):
        # Double-quoted key and list index together
        data = {"my-list": ["a", "b", "c"], "pick": '<<["my-list"][2]>>'}
        rendered = self.renderer.render(data)
        self.assertEqual(rendered["pick"], "c")


if __name__ == "__main__":
    unittest.main()
