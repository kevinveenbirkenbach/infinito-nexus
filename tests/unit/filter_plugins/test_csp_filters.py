import unittest
import hashlib
import base64
import sys
import os

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../")
    ),
)

from filter_plugins.csp_filters import FilterModule, AnsibleFilterError

class TestCspFilters(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule()
        self.apps = {
            'app1': {
                'features': {
                    'oauth2': True,
                    'matomo': True,
                },
                'server':{
                    'csp': {
                        'whitelist': {
                            'script-src-elem': ['https://cdn.example.com'],
                            'connect-src': 'https://api.example.com',
                        },
                        'flags': {
                            'script-src': {
                                'unsafe-eval': True,
                                'unsafe-inline': False,
                            },
                            'style-src': {
                                'unsafe-inline': True,
                            },
                        },
                        'hashes': {
                            'script-src': [
                                "console.log('hello');",
                            ],
                            'style-src': [
                                "body { background: #fff; }",
                            ]
                        }
                        }
                },
            },
            'app2': {}
        }
        self.domains = {
            'web-app-matomo': ['matomo.example.org'],
            'web-svc-cdn': ['cdn.example.org'],
        }

    def test_get_csp_whitelist_list(self):
        result = self.filter.get_csp_whitelist(self.apps, 'app1', 'script-src-elem')
        self.assertEqual(result, ['https://cdn.example.com'])

    def test_get_csp_whitelist_string(self):
        result = self.filter.get_csp_whitelist(self.apps, 'app1', 'connect-src')
        self.assertEqual(result, ['https://api.example.com'])

    def test_get_csp_whitelist_none(self):
        result = self.filter.get_csp_whitelist(self.apps, 'app1', 'font-src')
        self.assertEqual(result, [])

    def test_get_csp_flags_eval(self):
        result = self.filter.get_csp_flags(self.apps, 'app1', 'script-src')
        self.assertIn("'unsafe-eval'", result)
        self.assertNotIn("'unsafe-inline'", result)

    def test_get_csp_flags_inline(self):
        result = self.filter.get_csp_flags(self.apps, 'app1', 'style-src')
        self.assertIn("'unsafe-inline'", result)
        self.assertNotIn("'unsafe-eval'", result)

    def test_get_csp_flags_none(self):
        result = self.filter.get_csp_flags(self.apps, 'app1', 'connect-src')
        self.assertEqual(result, [])

    def test_build_csp_header_basic(self):
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        # Ensure core directives are present
        self.assertIn("default-src 'self';", header)
        # script-src directive should include unsafe-eval, Matomo domain and CDN (hash may follow)
        self.assertIn(
            "script-src-elem 'self' https://matomo.example.org https://cdn.example.com",
            header
        )
        self.assertIn(
            "script-src 'self' 'unsafe-eval'",
            header
        )
        # connect-src directive unchanged (no inline hash)
        self.assertIn(
            "connect-src 'self' https://matomo.example.org https://api.example.com;",
            header
        )
        # ends with img-src
        self.assertTrue(header.strip().endswith('img-src * data: blob:;'))

    def test_build_csp_header_without_matomo_or_flags(self):
        header = self.filter.build_csp_header(self.apps, 'app2', self.domains)
        # default-src only contains 'self'
        self.assertIn("default-src 'self';", header)
        # no external URLs
        self.assertNotIn('http', header)
        # ends with img-src
        self.assertTrue(header.strip().endswith('img-src * data: blob:;'))
        
    def test_get_csp_inline_content_list(self):
        snippets = self.filter.get_csp_inline_content(self.apps, 'app1', 'script-src')
        self.assertEqual(snippets, ["console.log('hello');"])

    def test_get_csp_inline_content_string(self):
        # simulate single string instead of list
        self.apps['app1']['server']['csp']['hashes']['style-src'] = "body { color: red; }"
        snippets = self.filter.get_csp_inline_content(self.apps, 'app1', 'style-src')
        self.assertEqual(snippets, ["body { color: red; }"])

    def test_get_csp_inline_content_none(self):
        snippets = self.filter.get_csp_inline_content(self.apps, 'app1', 'font-src')
        self.assertEqual(snippets, [])

    def test_get_csp_hash_known_value(self):
        content = "alert(1);"
        # compute expected
        digest = hashlib.sha256(content.encode('utf-8')).digest()
        b64 = base64.b64encode(digest).decode('utf-8')
        expected = f"'sha256-{b64}'"
        result = self.filter.get_csp_hash(content)
        self.assertEqual(result, expected)

    def test_get_csp_hash_error(self):
        with self.assertRaises(AnsibleFilterError):
            # passing a non-decodable object
            self.filter.get_csp_hash(None)

    def test_build_csp_header_includes_hashes_only_if_no_unsafe_inline(self):
        """
        script-src has unsafe-inline = False -> hash should be included
        style-src has unsafe-inline = True  -> hash should NOT be included
        """
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')

        # script-src includes hash because 'unsafe-inline' is False
        script_hash = self.filter.get_csp_hash("console.log('hello');")
        self.assertIn(script_hash, header)

        # style-src does NOT include hash because 'unsafe-inline' is True
        style_hash = self.filter.get_csp_hash("body { background: #fff; }")
        self.assertNotIn(style_hash, header)


    def test_build_csp_header_recaptcha_toggle(self):
        """
        When the 'recaptcha' feature is enabled, 'https://www.google.com'
        must be included in script-src; when disabled, it must not be.
        """
        # enabled case
        self.apps['app1']['features']['recaptcha'] = True
        header_enabled = self.filter.build_csp_header(
            self.apps, 'app1', self.domains, web_protocol='https'
        )
        self.assertIn("https://www.google.com", header_enabled)

        # disabled case
        self.apps['app1']['features']['recaptcha'] = False
        header_disabled = self.filter.build_csp_header(
            self.apps, 'app1', self.domains, web_protocol='https'
        )
        self.assertNotIn("https://www.google.com", header_disabled)

    def test_build_csp_header_frame_ancestors(self):
        """
        frame-ancestors should include the wildcarded SLD+TLD when
        'desktop' is enabled, and omit it when disabled.
        """
        # Ensure feature enabled and domain set
        self.apps['app1']['features']['desktop'] = True
        # simulate a subdomain for the application
        self.domains['web-app-desktop'] = ['domain-example.com']
        
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        # Expect '*.domain-example.com' in the frame-ancestors directive
        self.assertRegex(
            header,
            r"frame-ancestors\s+'self'\s+domain-example\.com;"
        )

        # Now disable the feature and rebuild
        self.apps['app1']['features']['desktop'] = False
        header_no = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        # Should no longer contain the wildcarded sld.tld
        self.assertNotIn("*.domain-example.com", header_no)


if __name__ == '__main__':
    unittest.main()