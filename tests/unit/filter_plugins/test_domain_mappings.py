import unittest
from ansible.errors import AnsibleFilterError
from filter_plugins.domain_redirect_mappings import FilterModule


class TestDomainMappings(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule()
        self.primary = "example.com"

    def test_empty_apps(self):
        apps = {}
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, [])

    def test_app_without_domains(self):
        apps = {"web-app-desktop": {}}
        # no server/domains key → no mappings
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, [])

    def test_empty_domains_cfg(self):
        # Explicitly empty server.domains dict.
        # With auto_build_alias=True the default alias becomes the target itself,
        # so it would be skipped as a self-mapping -> no mappings.
        apps = {"web-app-desktop": {"server": {"domains": {}}}}
        expected = []
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, expected)

    def test_explicit_aliases(self):
        apps = {"web-app-desktop": {"server": {"domains": {"aliases": ["alias.com"]}}}}
        default = "desktop.example.com"
        expected = [
            {"source": "alias.com", "target": default},
        ]
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertCountEqual(result, expected)

    def test_canonical_not_default(self):
        apps = {"web-app-desktop": {"server": {"domains": {"canonical": ["foo.com"]}}}}
        expected = [{"source": "desktop.example.com", "target": "foo.com"}]
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, expected)

    def test_canonical_dict(self):
        apps = {
            "web-app-desktop": {
                "server": {
                    "domains": {"canonical": {"one": "one.com", "two": "two.com"}}
                }
            }
        }
        # first canonical key 'one' -> one.com (dict insertion order)
        expected = [{"source": "desktop.example.com", "target": "one.com"}]
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertEqual(result, expected)

    def test_multiple_apps(self):
        apps = {
            "web-app-desktop": {"server": {"domains": {"aliases": ["a1.com"]}}},
            "web-app-mastodon": {"server": {"domains": {"canonical": ["c2.com"]}}},
        }
        expected = [
            {"source": "a1.com", "target": "desktop.example.com"},
            {"source": "mastodon.example.com", "target": "c2.com"},
        ]
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertCountEqual(result, expected)

    def test_multiple_aliases(self):
        apps = {
            "web-app-desktop": {
                "server": {"domains": {"aliases": ["a1.com", "a2.com"]}}
            }
        }
        expected = [
            {"source": "a1.com", "target": "desktop.example.com"},
            {"source": "a2.com", "target": "desktop.example.com"},
        ]
        result = self.filter.domain_mappings(apps, self.primary, True)
        self.assertCountEqual(result, expected)

    def test_invalid_aliases_type(self):
        apps = {"web-app-desktop": {"server": {"domains": {"aliases": 123}}}}
        with self.assertRaises(AnsibleFilterError):
            self.filter.domain_mappings(apps, self.primary, True)

    def test_canonical_not_default_no_autobuild(self):
        """
        When only a canonical different from the default exists and auto_build_aliases is False,
        we should NOT auto-generate a default alias -> canonical mapping.
        """
        apps = {"web-app-desktop": {"server": {"domains": {"canonical": ["foo.com"]}}}}
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertEqual(result, [])  # no auto-added default alias

    def test_aliases_and_canonical_no_autobuild(self):
        """
        With auto_build_aliases=False we do NOT append the default domain to aliases.
        Only explicit aliases should map to canonical.
        """
        apps = {
            "web-app-desktop": {
                "server": {
                    "domains": {"aliases": ["alias.com"], "canonical": ["foo.com"]}
                }
            }
        }
        expected = [
            {"source": "alias.com", "target": "foo.com"},
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
            "web-app-desktop": {"server": {"domains": {"canonical": ["c1.com"]}}},
            "web-app-mastodon": {"server": {"domains": {"aliases": ["m1.com"]}}},
        }
        expected = [
            {"source": "m1.com", "target": "mastodon.example.com"},
        ]
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertCountEqual(result, expected)

    def test_no_domains_key_no_autobuild(self):
        """
        App without 'server.domains' produces no mappings regardless of auto_build_aliases.
        """
        apps = {
            "web-app-desktop": {
                # no 'server' or 'domains'
            }
        }
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertEqual(result, [])

    def test_empty_server_domains_no_autobuild(self):
        """
        Explicit empty server.domains should not generate aliases when auto_build_aliases is False.
        """
        apps = {"web-app-desktop": {"server": {"domains": {}}}}
        result = self.filter.domain_mappings(apps, self.primary, False)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
