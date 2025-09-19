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
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, [])

    def test_app_without_domains(self):
        apps = {'web-app-desktop': {}}
        # no domains key → no mappings
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, [])

    def test_empty_domains_cfg(self):
        apps = {'web-app-desktop': {'domains': {}}}
        default = 'desktop.example.com'
        expected = []
        result = self.filter.domain_mappings(apps, self.primary, True)
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
        result = self.filter.domain_mappings(apps, self.primary, True)
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
        result = self.filter.domain_mappings(apps, self.primary, True)
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
        result = self.filter.domain_mappings(apps, self.primary, True)
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
        result = self.filter.domain_mappings(apps, self.primary, True)
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
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertCountEqual(result, expected)

    def test_invalid_aliases_type(self):
        apps = {
            'web-app-desktop': {'server':{'domains': {'aliases': 123}}}
        }
        with self.assertRaises(AnsibleFilterError):
            self.filter.domain_mappings(apps, self.primary, True)

    def test_canonical_not_default_no_autobuild(self):
        """
        When only a canonical different from the default exists and auto_build_aliases is False,
        we should NOT auto-generate a default alias -> canonical mapping.
        """
        apps = {
            'web-app-desktop': {
                'server': {
                    'domains': {'canonical': ['foo.com']}
                }
            }
        }
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertEqual(result, [])  # no auto-added default alias

    def test_aliases_and_canonical_no_autobuild_still_adds_default(self):
        """
        If explicit aliases are present, the filter always appends the default domain
        to the alias list (to cover 'www'/'root' style defaults), regardless of auto_build_aliases.
        With a canonical set, both the explicit alias and the default should point to the canonical.
        """
        apps = {
            'web-app-desktop': {
                'server': {
                    'domains': {
                        'aliases': ['alias.com'],
                        'canonical': ['foo.com']
                    }
                }
            }
        }
        expected = [
            {'source': 'alias.com',           'target': 'foo.com'},
            {'source': 'desktop.example.com', 'target': 'foo.com'},
        ]
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertCountEqual(result, expected)

    def test_mixed_apps_no_autobuild(self):
        """
        One app with only canonical (no aliases) and one app with only aliases:
        - The canonical-only app produces no mappings when auto_build_aliases is False.
        - The alias-only app maps its aliases to its default domain; default self-mapping is skipped.
        """
        apps = {
            'web-app-desktop': {
                'server': {'domains': {'canonical': ['c1.com']}}
            },
            'web-app-mastodon': {
                'server': {'domains': {'aliases': ['m1.com']}}
            },
        }
        expected = [
            {'source': 'm1.com', 'target': 'mastodon.example.com'},
        ]
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertCountEqual(result, expected)

    def test_no_domains_key_no_autobuild(self):
        """
        App ohne 'server.domains' erzeugt keine Mappings, unabhängig von auto_build_aliases.
        """
        apps = {
            'web-app-desktop': {
                # no 'server' or 'domains'
            }
        }
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()
