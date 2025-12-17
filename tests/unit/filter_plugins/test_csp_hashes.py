# tests/unit/filter_plugins/test_csp_hashes.py
import unittest
from ansible.errors import AnsibleFilterError
from filter_plugins.csp_hashes import append_csp_hash


class TestCspHashes(unittest.TestCase):
    def setUp(self):
        # Sample applications dict for testing
        self.applications = {
            "app1": {
                "server": {"csp": {"hashes": {"script-src-elem": ["existing-hash"]}}}
            }
        }
        self.code = "new-hash"  # example one-liner hash

    def test_appends_new_hash(self):
        result = append_csp_hash(self.applications, "app1", self.code)
        # Original remains unchanged
        self.assertNotIn(
            self.code,
            self.applications["app1"]["server"]["csp"]["hashes"]["script-src-elem"],
        )
        # New result should contain both existing and new
        self.assertIn(
            "existing-hash",
            result["app1"]["server"]["csp"]["hashes"]["script-src-elem"],
        )
        self.assertIn(
            self.code, result["app1"]["server"]["csp"]["hashes"]["script-src-elem"]
        )

    def test_does_not_duplicate_existing_hash(self):
        # Append an existing hash
        result = append_csp_hash(self.applications, "app1", "existing-hash")
        # Should still only have one instance
        hashes = result["app1"]["server"]["csp"]["hashes"]["script-src-elem"]
        self.assertEqual(hashes.count("existing-hash"), 1)

    def test_creates_missing_csp_structure(self):
        # Remove csp and hashes keys
        apps = {"app2": {}}
        result = append_csp_hash(apps, "app2", self.code)
        self.assertIn("csp", result["app2"]["server"])
        self.assertIn("hashes", result["app2"]["server"]["csp"])
        self.assertIn(
            self.code, result["app2"]["server"]["csp"]["hashes"]["script-src-elem"]
        )

    def test_non_dict_applications_raises(self):
        with self.assertRaises(AnsibleFilterError):
            append_csp_hash("not-a-dict", "app1", self.code)

    def test_unknown_application_id_raises(self):
        with self.assertRaises(AnsibleFilterError):
            append_csp_hash(self.applications, "unknown", self.code)


if __name__ == "__main__":
    unittest.main()
