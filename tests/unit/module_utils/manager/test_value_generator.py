import base64
import re
import unittest

from module_utils.manager.value_generator import ValueGenerator


class TestValueGenerator(unittest.TestCase):
    def setUp(self):
        self.vg = ValueGenerator()

    def test_generate_secure_alphanumeric(self):
        s = self.vg.generate_secure_alphanumeric(64)
        self.assertEqual(len(s), 64)
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9]{64}", s))

    def test_generate_value_random_hex(self):
        v = self.vg.generate_value("random_hex")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{128}", v))

    def test_generate_value_random_hex_32(self):
        v = self.vg.generate_value("random_hex_32")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", v))

    def test_generate_value_random_hex_16(self):
        v = self.vg.generate_value("random_hex_16")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{32}", v))

    def test_generate_value_sha256(self):
        v = self.vg.generate_value("sha256")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", v))

    def test_generate_value_sha1(self):
        v = self.vg.generate_value("sha1")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", v))

    def test_generate_value_base64_prefixed_32(self):
        v = self.vg.generate_value("base64_prefixed_32")
        self.assertTrue(v.startswith("base64:"))
        raw = v.split("base64:", 1)[1].encode()
        decoded = base64.b64decode(raw)
        self.assertEqual(len(decoded), 32)

    def test_generate_value_alphanumeric(self):
        v = self.vg.generate_value("alphanumeric")
        self.assertEqual(len(v), 64)
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9]{64}", v))

    def test_generate_value_bcrypt(self):
        v = self.vg.generate_value("bcrypt")
        # your implementation replaces '$' chars
        self.assertNotIn("$", v)
        self.assertGreater(len(v), 20)

    def test_generate_value_unknown(self):
        v = self.vg.generate_value("does_not_exist")
        self.assertEqual(v, "undefined")


if __name__ == "__main__":
    unittest.main()
