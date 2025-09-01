import unittest
import sys
import os

# Ensure filter_plugins directory is on the path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../filter_plugins'))
)

from ansible.errors import AnsibleFilterError
from url_join import url_join


class TestUrlJoinFilter(unittest.TestCase):
    # --- success cases ---
    def test_http_basic(self):
        self.assertEqual(
            url_join(['http://example.com', 'foo', 'bar']),
            'http://example.com/foo/bar'
        )

    def test_https_slashes(self):
        self.assertEqual(
            url_join(['https://example.com/', '/api/', '/v1/', '/users/']),
            'https://example.com/api/v1/users'
        )

    def test_custom_scheme(self):
        self.assertEqual(
            url_join(['myapp+v1://host/', '//section', 'item']),
            'myapp+v1://host/section/item'
        )

    def test_scheme_with_path_in_first(self):
        self.assertEqual(
            url_join(['https://example.com/base/', '/deep/', 'leaf']),
            'https://example.com/base/deep/leaf'
        )

    def test_none_in_list(self):
        self.assertEqual(
            url_join(['https://example.com', None, 'foo']),
            'https://example.com/foo'
        )

    def test_numeric_parts(self):
        self.assertEqual(
            url_join(['https://example.com', 123, '456']),
            'https://example.com/123/456'
        )

    def test_only_scheme_returns_scheme(self):
        self.assertEqual(
            url_join(['https://']),
            'https://'
        )

    # --- error cases with specific messages ---
    def test_none_input_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"parts must be a non-empty list; got None"):
            url_join(None)

    def test_empty_list_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"parts must be a non-empty list"):
            url_join([])

    def test_non_list_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"parts must be a list/tuple; got str"):
            url_join("https://example.com")

    def test_first_none_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"first element must include a scheme"):
            url_join([None, 'foo'])

    def test_no_scheme_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"must start with '<scheme>://'"):
            url_join(['example.com', 'foo'])

    def test_additional_scheme_in_later_part_raises(self):
        with self.assertRaisesRegex(AnsibleFilterError, r"only the first element may contain a scheme"):
            url_join(['https://example.com', 'https://elsewhere'])

    def test_unstringifiable_first_part_raises(self):
        class Bad:
            def __str__(self):
                raise ValueError("boom")
        with self.assertRaisesRegex(AnsibleFilterError, r"unable to convert part at index 0"):
            url_join([Bad(), 'x'])

    def test_unstringifiable_later_part_raises(self):
        class Bad:
            def __str__(self):
                raise ValueError("boom")
        with self.assertRaisesRegex(AnsibleFilterError, r"unable to convert part at index 2"):
            url_join(['https://example.com', 'ok', Bad()])


if __name__ == '__main__':
    unittest.main()
