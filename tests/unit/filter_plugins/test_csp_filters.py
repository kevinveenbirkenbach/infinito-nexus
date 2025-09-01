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

    # --- Helpers -------------------------------------------------------------

    def _get_directive_tokens(self, header: str, directive: str):
        """
        Extract tokens (as a list of strings) for a given directive from a CSP header.
        Example: for "connect-src 'self' https://a https://b;" -> ["'self'", "https://a", "https://b"]
        Returns [] if not found.
        """
        for part in header.split(';'):
            part = part.strip()
            if not part:
                continue
            if part.startswith(directive + ' '):
                # remove directive name, split remainder by spaces
                remainder = part[len(directive):].strip()
                return [tok for tok in remainder.split(' ') if tok]
            if part == directive:  # unlikely, but guard
                return []
        return []

    # --- Tests ---------------------------------------------------------------

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

        # script-src-elem should include 'self', Matomo, internes CDN und explizite Whitelist-CDN
        self.assertIn("script-src-elem 'self'", header)
        self.assertIn("https://matomo.example.org", header)
        self.assertIn("https://cdn.example.org", header)   # internes CDN
        self.assertIn("https://cdn.example.com", header)   # Whitelist

        # script-src directive should include unsafe-eval
        self.assertIn("script-src 'self' 'unsafe-eval'", header)

        # connect-src directive (reihenfolgeunabhängig prüfen)
        tokens = self._get_directive_tokens(header, "connect-src")
        self.assertIn("'self'", tokens)
        self.assertIn("https://matomo.example.org", tokens)
        self.assertIn("https://cdn.example.org", tokens)
        self.assertIn("https://api.example.com", tokens)

        # ends with img-src
        self.assertTrue(header.strip().endswith('img-src * data: blob:;'))

    def test_build_csp_header_without_matomo_or_flags(self):
        header = self.filter.build_csp_header(self.apps, 'app2', self.domains)
        # default-src only contains 'self'
        self.assertIn("default-src 'self';", header)
        self.assertIn('https://cdn.example.org', header)
        self.assertNotIn('matomo.example.org', header)
        self.assertNotIn('www.google.com', header)
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
        # Expect 'domain-example.com' in the frame-ancestors directive
        self.assertRegex(
            header,
            r"frame-ancestors\s+'self'\s+domain-example\.com;"
        )

        # Now disable the feature and rebuild
        self.apps['app1']['features']['desktop'] = False
        header_no = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        # Should no longer contain the SLD+TLD
        self.assertNotIn("domain-example.com", header_no)

    def test_flags_default_unsafe_inline_for_styles(self):
        """
        get_csp_flags should default to include 'unsafe-inline' for style-src and style-src-elem,
        even when no explicit flags are configured.
        """
        # No explicit flags for app2
        self.assertIn("'unsafe-inline'", self.filter.get_csp_flags(self.apps, 'app2', 'style-src'))
        self.assertIn("'unsafe-inline'", self.filter.get_csp_flags(self.apps, 'app2', 'style-src-elem'))

        # Non-style directive should NOT get unsafe-inline by default
        self.assertNotIn("'unsafe-inline'", self.filter.get_csp_flags(self.apps, 'app2', 'script-src'))


    def test_style_src_hashes_suppressed_by_default(self):
        """
        Because 'unsafe-inline' is defaulted for style-src, hashes for style-src should NOT be included.
        """
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        style_hash = self.filter.get_csp_hash("body { background: #fff; }")
        self.assertNotIn(style_hash, header)

        # Ensure 'unsafe-inline' actually present in style-src directive
        tokens = self._get_directive_tokens(header, 'style-src')
        self.assertIn("'unsafe-inline'", tokens)


    def test_style_src_override_disables_inline_and_enables_hashes(self):
        """
        If an app explicitly disables 'unsafe-inline' for style-src, then hashes MUST appear.
        """
        # Configure override: disable unsafe-inline for style-src
        self.apps.setdefault('app1', {}).setdefault('server', {}).setdefault('csp', {}).setdefault('flags', {}).setdefault('style-src', {})
        self.apps['app1']['server']['csp']['flags']['style-src']['unsafe-inline'] = False

        # Also ensure there is a style-src hash to include
        self.apps['app1']['server']['csp']['hashes']['style-src'] = "body { background: #fff; }"

        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')

        # Then the style hash SHOULD be present
        style_hash = self.filter.get_csp_hash("body { background: #fff; }")
        self.assertIn(style_hash, header)

        # And 'unsafe-inline' should NOT be present in style-src tokens
        tokens = self._get_directive_tokens(header, 'style-src')
        self.assertNotIn("'unsafe-inline'", tokens)


    def test_style_src_elem_default_unsafe_inline(self):
        """
        style-src-elem should include 'unsafe-inline' by default (from get_csp_flags defaults).
        """
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        tokens = self._get_directive_tokens(header, 'style-src-elem')
        self.assertIn("'unsafe-inline'", tokens)


    def test_script_src_hash_behavior_depends_on_unsafe_inline_flag(self):
        """
        For script-src:
        - When unsafe-inline=False (as in app1), hashes SHOULD be included.
        - If we flip unsafe-inline=True, hashes should NOT be included.
        """
        # Baseline (from setUp): app1 script-src has unsafe-inline=False and one hash
        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        script_hash = self.filter.get_csp_hash("console.log('hello');")
        self.assertIn(script_hash, header)

        # Now toggle unsafe-inline=True and ensure hash disappears
        self.apps['app1']['server']['csp']['flags']['script-src']['unsafe-inline'] = True
        header_inline = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')
        self.assertNotIn(script_hash, header_inline)

        # And 'unsafe-inline' should be present in the script-src tokens now
        tokens = self._get_directive_tokens(header_inline, 'script-src')
        self.assertIn("'unsafe-inline'", tokens)


    def test_hashes_guard_checks_final_tokens_not_only_flags(self):
        """
        Ensure the 'no-hash-when-unsafe-inline' rule is driven by FINAL tokens,
        not just raw flags: simulate default-provided 'unsafe-inline' (style-src)
        without explicitly setting it in flags and verify hashes are still suppressed.
        """
        # Remove explicit style-src flags entirely to rely solely on defaults
        self.apps['app1']['server']['csp']['flags'].pop('style-src', None)

        # Provide a style-src hash
        self.apps['app1']['server']['csp']['hashes']['style-src'] = "body { color: blue; }"
        style_hash = self.filter.get_csp_hash("body { color: blue; }")

        header = self.filter.build_csp_header(self.apps, 'app1', self.domains, web_protocol='https')

        # Because defaults include 'unsafe-inline' for style-src, the hash MUST NOT appear
        self.assertNotIn(style_hash, header)

        # And 'unsafe-inline' must appear in final tokens
        tokens = self._get_directive_tokens(header, 'style-src')
        self.assertIn("'unsafe-inline'", tokens)


if __name__ == '__main__':
    unittest.main()
