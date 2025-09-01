import os
import sys
import tempfile
import time
import unittest

# ensure repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from ansible.errors import AnsibleError  # type: ignore
from lookup_plugins.local_mtime_qs import LookupModule


class TestLocalMtimeQs(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmpdir.name, "file.css")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("body{}")
        # set stable mtime
        self.mtime = int(time.time()) - 123
        os.utime(self.path, (self.mtime, self.mtime))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_single_path_qs_default(self):
        res = LookupModule().run([self.path])
        self.assertEqual(res, [f"?version={self.mtime}"])

    def test_single_path_epoch(self):
        res = LookupModule().run([self.path], mode="epoch")
        self.assertEqual(res, [str(self.mtime)])

    def test_multiple_paths(self):
        path2 = os.path.join(self.tmpdir.name, "a.js")
        with open(path2, "w", encoding="utf-8") as f:
            f.write("// js")
        os.utime(path2, (self.mtime + 1, self.mtime + 1))
        res = LookupModule().run([self.path, path2], param="v")
        self.assertEqual(res, [f"?v={self.mtime}", f"?v={self.mtime + 1}"])

    def test_missing_raises(self):
        with self.assertRaises(AnsibleError):
            LookupModule().run([os.path.join(self.tmpdir.name, "nope.css")])


if __name__ == "__main__":
    unittest.main()
