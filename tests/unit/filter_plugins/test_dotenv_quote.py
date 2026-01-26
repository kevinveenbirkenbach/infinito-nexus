import unittest

from filter_plugins.dotenv import FilterModule


class TestDotenvQuote(unittest.TestCase):
    def setUp(self):
        self.f = FilterModule().filters()["dotenv_quote"]

    def test_none(self):
        self.assertEqual(self.f(None), '""')

    def test_empty_string(self):
        self.assertEqual(self.f(""), '""')

    def test_plain_string_is_double_quoted(self):
        self.assertEqual(self.f("abc"), '"abc"')

    def test_single_quote_is_preserved(self):
        # leading single quote should remain part of the value
        self.assertEqual(self.f("'secret"), '"\'secret"')

    def test_dollar_is_escaped_for_compose(self):
        self.assertEqual(self.f("$tr0ng"), '"$$tr0ng"')
        self.assertEqual(self.f("'$tr0ng€xampl3PW!"), '"\'$$tr0ng€xampl3PW!"')

    def test_multiple_dollars(self):
        self.assertEqual(self.f("a$b$c"), '"a$$b$$c"')

    def test_existing_double_dollars_are_doubled_again(self):
        # The filter is deterministic and does not try to "detect" prior escaping.
        # This is fine for correctness (it still results in literal '$$' at runtime).
        self.assertEqual(self.f("$$FOO"), '"$$$$FOO"')

    def test_backslash_is_escaped(self):
        self.assertEqual(self.f(r"pa\ss"), r'"pa\\ss"')

    def test_double_quote_is_escaped(self):
        self.assertEqual(self.f('pa"ss'), r'"pa\"ss"')

    def test_backslash_and_quote_combination(self):
        # order matters: backslash first, then double quote
        self.assertEqual(self.f(r"pa\"ss"), r'"pa\\\"ss"')

    def test_non_string_input_is_stringified(self):
        self.assertEqual(self.f(123), '"123"')
        self.assertEqual(self.f(True), '"True"')

    def test_unicode_is_preserved(self):
        self.assertEqual(self.f("€"), '"€"')
        self.assertEqual(self.f("p€ss$word"), '"p€ss$$word"')


if __name__ == "__main__":
    unittest.main()
