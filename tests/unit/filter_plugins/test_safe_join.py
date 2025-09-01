import unittest
import sys
import os

# Ensure filter_plugins directory is on the path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../filter_plugins'))
)

from safe_join import safe_join

class TestSafeJoinFilter(unittest.TestCase):
    def test_join_with_trailing_slashes(self):
        self.assertEqual(
            safe_join('http://example.com/', '/path/to'),
            'http://example.com/path/to'
        )

    def test_join_without_slashes(self):
        self.assertEqual(
            safe_join('http://example.com', 'path/to'),
            'http://example.com/path/to'
        )

    def test_base_none(self):
        with self.assertRaises(ValueError):
            safe_join(None, 'path')

    def test_tail_none(self):
        with self.assertRaises(ValueError):
            safe_join('http://example.com', None)

    def test_base_empty(self):
        self.assertEqual(safe_join('', 'path'), '/path')

    def test_tail_empty(self):
        # joining with empty tail should yield base with trailing slash
        self.assertEqual(
            safe_join('http://example.com', ''),
            'http://example.com/'
        )

    def test_numeric_base(self):
        # numeric base is cast to string
        self.assertEqual(safe_join(123, 'path'), '123/path')

    def test_exception_in_str(self):
        class Bad:
            def __str__(self):
                raise ValueError('bad')
        # on exception, safe_join returns ''
        self.assertEqual(safe_join(Bad(), 'x'), '')

if __name__ == '__main__':
    unittest.main()
