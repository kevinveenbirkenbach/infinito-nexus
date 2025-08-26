import os
import sys
import unittest

# Add the filter_plugins directory to the import path
dir_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../filter_plugins')
)
sys.path.insert(0, dir_path)

from ansible.errors import AnsibleFilterError
from domain_redirect_mappings import FilterModule

class TestDomainMappings(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule()
        self.primary = 'example.com'

    def test_empty_apps(self):
        apps = {}
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertEqual(result, [])

    def test_app_without_domains(self):
        apps = {'web-app-desktop': {}}
        # no domains key → no mappings
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertEqual(result, [])

    def test_empty_domains_cfg(self):
        apps = {'web-app-desktop': {'domains': {}}}
        default = 'desktop.example.com'
        expected = []
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertEqual(result, expected)

    def test_explicit_aliases(self):
        apps = {
            'web-app-desktop': {
                'server':{
                    'domains': {'aliases': ['alias.com']}
                }
            }
        }
        default = 'desktop.example.com'
        expected = [
            {'source': 'alias.com',    'target': default},
        ]
        result = self.filter.domain_mappings(apps, self.primary)
        # order not important
        self.assertCountEqual(result, expected)

    def test_canonical_not_default(self):
        apps = {
            'web-app-desktop': {
                'server':{
                    'domains': {'canonical': ['foo.com']}
                }
            }
        }
        expected = [
            {'source': 'desktop.example.com', 'target': 'foo.com'}
        ]
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertEqual(result, expected)

    def test_canonical_dict(self):
        apps = {
            'web-app-desktop': {
                'server':{
                    'domains': {
                        'canonical': {'one': 'one.com', 'two': 'two.com'}
                    }
                }
            }
        }
        # first canonical key 'one' → one.com
        expected = [
            {'source': 'desktop.example.com', 'target': 'one.com'}
        ]
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertEqual(result, expected)

    def test_multiple_apps(self):
        apps = {
            'web-app-desktop': {
                'server':{'domains': {'aliases': ['a1.com']}}
            },
            'web-app-mastodon': {
                'server':{'domains': {'canonical': ['c2.com']}}
            },
        }
        expected = [
            {'source': 'a1.com',              'target': 'desktop.example.com'},
            {'source': 'mastodon.example.com',    'target': 'c2.com'},
        ]
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertCountEqual(result, expected)
        
    def test_multiple_aliases(self):
        apps = {
            'web-app-desktop': {
                'server':{'domains': {'aliases': ['a1.com','a2.com']}
                }
            }
        }
        expected = [
            {'source': 'a1.com', 'target': 'desktop.example.com'},
            {'source': 'a2.com', 'target': 'desktop.example.com'}
        ]
        result = self.filter.domain_mappings(apps, self.primary)
        self.assertCountEqual(result, expected)

    def test_invalid_aliases_type(self):
        apps = {
            'web-app-desktop': {'server':{'domains': {'aliases': 123}}}
        }
        with self.assertRaises(AnsibleFilterError):
            self.filter.domain_mappings(apps, self.primary)


if __name__ == "__main__":
    unittest.main()
