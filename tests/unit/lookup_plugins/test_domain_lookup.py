# tests/unit/lookup_plugins/test_domain_lookup.py
import os
import sys
import unittest

from ansible.errors import AnsibleError


def _ensure_repo_root_on_syspath():
    # tests/unit/lookup_plugins/test_domain_lookup.py -> repo_root
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_syspath()

from lookup_plugins.domain import LookupModule  # noqa: E402


class TestDomainLookup(unittest.TestCase):
    def setUp(self):
        self.lookup = LookupModule()

    def run_lookup(self, application_id, domains):
        return self.lookup.run(
            terms=[application_id],
            variables={"domains": domains},
        )

    def test_string_domain(self):
        domains = {"app": "example.com"}
        self.assertEqual(self.run_lookup("app", domains), ["example.com"])

    def test_list_domain(self):
        domains = {"app": ["example.com", "alt.example.com"]}
        self.assertEqual(self.run_lookup("app", domains), ["example.com"])

    def test_dict_domain(self):
        domains = {"app": {"primary": "example.com", "secondary": "alt.example.com"}}
        self.assertEqual(self.run_lookup("app", domains), ["example.com"])

    def test_missing_domains_variable(self):
        with self.assertRaises(AnsibleError) as ctx:
            self.lookup.run(terms=["app"], variables={})
        self.assertIn("missing required variable 'domains'", str(ctx.exception))

    def test_missing_application_id(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(terms=[], variables={"domains": {"app": "example.com"}})

    def test_unknown_application_id(self):
        with self.assertRaises(AnsibleError) as ctx:
            self.run_lookup("unknown", {"app": "example.com"})
        self.assertIn("not found in domains mapping", str(ctx.exception))

    def test_empty_string_domain(self):
        with self.assertRaises(AnsibleError):
            self.run_lookup("app", {"app": ""})

    def test_empty_list_domain(self):
        with self.assertRaises(AnsibleError):
            self.run_lookup("app", {"app": []})

    def test_empty_dict_domain(self):
        with self.assertRaises(AnsibleError):
            self.run_lookup("app", {"app": {}})

    def test_invalid_application_id_type(self):
        with self.assertRaises(AnsibleError):
            self.lookup.run(terms=[123], variables={"domains": {"app": "example.com"}})


if __name__ == "__main__":
    unittest.main()
