import unittest
from ansible.errors import AnsibleFilterError
from filter_plugins.canonical_domains_map import FilterModule

class TestDomainFilters(unittest.TestCase):
    def setUp(self):
        self.filter_module = FilterModule()
        # Sample primary domain
        self.primary = 'example.com'

    def test_canonical_empty_apps(self):
        apps = {}
        expected = {}
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(result, expected)

    def test_canonical_without_domains(self):
        apps = {'web-app-app1': {}}
        expected = {'web-app-app1': ['app1.example.com']}
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(result, expected)

    def test_canonical_with_list(self):
        apps = {
            'web-app-app1': {
                'server':{
                    'domains': {'canonical': ['foo.com', 'bar.com']}
                }
            }
        }
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertCountEqual(
            result['web-app-app1'],
            ['foo.com', 'bar.com']
        )

    def test_canonical_with_dict(self):
        apps = {
            'web-app-app1': {
                'server':{
                    'domains': {'canonical': {'one': 'one.com', 'two': 'two.com'}}
                }
            }
        }
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(
            result['web-app-app1'],
            {'one': 'one.com', 'two': 'two.com'}
        )

    def test_canonical_duplicate_raises(self):
        apps = {
            'web-app-app1':{
                'server':{'domains': {'canonical': ['dup.com']}},
            },
            'web-app-app2':{ 
                'server':{
                    'domains': {'canonical': ['dup.com']}
                },
            },
        }
        with self.assertRaises(AnsibleFilterError) as cm:
            self.filter_module.canonical_domains_map(apps, self.primary)
        # Updated to match new exception message
        self.assertIn("already configured for", str(cm.exception))

    def test_invalid_canonical_type(self):
        apps = {
            'web-app-app1': {'server':{'domains': {'canonical': 123}}}
        }
        with self.assertRaises(AnsibleFilterError):
            self.filter_module.canonical_domains_map(apps, self.primary)

    def test_non_web_apps_are_ignored(self):
        """
        Applications not starting with 'web-' should be skipped entirely,
        resulting in an empty mapping when only non-web apps are provided.
        """
        apps = {
            'db-app-app1': {'server':{'domains': {'canonical': ['db.example.com']}}},
            'service-app-app2': {}
        }
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(result, {})

    def test_mixed_web_and_non_web_apps(self):
        """
        Only 'web-' prefixed applications should be processed;
        non-web apps should be ignored alongside valid web apps.
        """
        apps = {
            'db-app-app1': {'server':{'domains': {'canonical': ['db.example.com']}}},
            'web-app-app1': {}
        }
        expected = {'web-app-app1': ['app1.example.com']}
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(result, expected)

    def test_non_web_invalid_config_no_error(self):
        """
        Invalid configurations for non-web apps should not raise errors
        since they are ignored by the filter.
        """
        apps = {
            'nonweb-app-app1': 'not-a-dict',
            'another': 12345
        }
        # Should simply return an empty result without exceptions
        result = self.filter_module.canonical_domains_map(apps, self.primary)
        self.assertEqual(result, {})

if __name__ == "__main__":
    unittest.main()