import unittest
import hashlib
import base64
import copy
from filter_plugins.csp_filters import FilterModule, AnsibleFilterError


class TestCspFilters(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule()
        self.apps = {
            "app1": {
                "features": {
                    "oauth2": True,
                    "matomo": True,
                },
                "server": {
                    "csp": {
                        "whitelist": {
                            "script-src-elem": ["https://cdn.example.com"],
                            "connect-src": "https://api.example.com",
                        },
                        "flags": {
                            "script-src": {
                                "unsafe-eval": True,
                                "unsafe-inline": False,
                            },
                            "style-src": {
                                "unsafe-inline": True,
                            },
                        },
                        "hashes": {
                            "script-src": [
                                "console.log('hello');",
                            ],
                            "style-src": [
                                "body { background: #fff; }",
                            ],
                        },
                    }
                },
            },
            "app2": {},
        }
        self.domains = {
            "web-app-matomo": ["matomo.example.org"],
            "web-svc-cdn": ["cdn.example.org"],
        }

    # --- Helpers -------------------------------------------------------------

    def _get_directive_tokens(self, header: str, directive: str):
        """
        Extract tokens (as a list of strings) for a given directive from a CSP header.
        Example: for "connect-src 'self' https://a https://b;" -> ["'self'", "https://a", "https://b"]
        Returns [] if not found.
        """
        for part in header.split(";"):
            part = part.strip()
            if not part:
                continue
            if part.startswith(directive + " "):
                # remove directive name, split remainder by spaces
                remainder = part[len(directive) :].strip()
                return [tok for tok in remainder.split(" ") if tok]
            if part == directive:  # unlikely, but guard
                return []
        return []

    # --- Tests ---------------------------------------------------------------

    def test_get_csp_whitelist_list(self):
        result = self.filter.get_csp_whitelist(self.apps, "app1", "script-src-elem")
        self.assertEqual(result, ["https://cdn.example.com"])

    def test_get_csp_whitelist_string(self):
        result = self.filter.get_csp_whitelist(self.apps, "app1", "connect-src")
        self.assertEqual(result, ["https://api.example.com"])

    def test_get_csp_whitelist_none(self):
        result = self.filter.get_csp_whitelist(self.apps, "app1", "font-src")
        self.assertEqual(result, [])

    def test_get_csp_flags_eval(self):
        result = self.filter.get_csp_flags(self.apps, "app1", "script-src")
        self.assertIn("'unsafe-eval'", result)
        self.assertNotIn("'unsafe-inline'", result)

    def test_get_csp_flags_inline(self):
        result = self.filter.get_csp_flags(self.apps, "app1", "style-src")
        self.assertIn("'unsafe-inline'", result)
        self.assertNotIn("'unsafe-eval'", result)

    def test_get_csp_flags_none(self):
        result = self.filter.get_csp_flags(self.apps, "app1", "connect-src")
        self.assertEqual(result, [])

    def test_build_csp_header_basic(self):
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")
        # Ensure core directives are present
        self.assertIn("default-src 'self';", header)

        # script-src-elem should include 'self', Matomo, internes CDN und explizite Whitelist-CDN
        self.assertIn("script-src-elem 'self'", header)
        self.assertIn("https://matomo.example.org", header)
        self.assertIn("https://cdn.example.org", header)  # internes CDN
        self.assertIn("https://cdn.example.com", header)  # Whitelist

        # script-src directive should include unsafe-eval (order-independent)
        script_tokens = self._get_directive_tokens(header, "script-src")
        self.assertIn("'unsafe-eval'", script_tokens)
        # 'self' should still be the first token
        self.assertGreater(len(script_tokens), 0)
        self.assertEqual(script_tokens[0], "'self'")

        # connect-src directive (reihenfolgeunabhängig prüfen)
        tokens = self._get_directive_tokens(header, "connect-src")
        self.assertIn("'self'", tokens)
        self.assertIn("https://matomo.example.org", tokens)
        self.assertIn("https://cdn.example.org", tokens)
        self.assertIn("https://api.example.com", tokens)

        # ends with img-src
        self.assertTrue(header.strip().endswith("img-src * data: blob:;"))

    def test_build_csp_header_without_matomo_or_flags(self):
        header = self.filter.build_csp_header(self.apps, "app2", self.domains, "https")
        # default-src only contains 'self'
        self.assertIn("default-src 'self';", header)
        self.assertIn("https://cdn.example.org", header)
        self.assertNotIn("matomo.example.org", header)
        self.assertNotIn("www.google.com", header)
        # ends with img-src
        self.assertTrue(header.strip().endswith("img-src * data: blob:;"))

    def test_get_csp_inline_content_list(self):
        snippets = self.filter.get_csp_inline_content(self.apps, "app1", "script-src")
        self.assertEqual(snippets, ["console.log('hello');"])

    def test_get_csp_inline_content_string(self):
        # simulate single string instead of list
        self.apps["app1"]["server"]["csp"]["hashes"]["style-src"] = (
            "body { color: red; }"
        )
        snippets = self.filter.get_csp_inline_content(self.apps, "app1", "style-src")
        self.assertEqual(snippets, ["body { color: red; }"])

    def test_get_csp_inline_content_none(self):
        snippets = self.filter.get_csp_inline_content(self.apps, "app1", "font-src")
        self.assertEqual(snippets, [])

    def test_get_csp_hash_known_value(self):
        content = "alert(1);"
        # compute expected
        digest = hashlib.sha256(content.encode("utf-8")).digest()
        b64 = base64.b64encode(digest).decode("utf-8")
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
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")

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
        self.apps["app1"]["features"]["recaptcha"] = True
        header_enabled = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )
        self.assertIn("https://www.google.com", header_enabled)

        # disabled case
        self.apps["app1"]["features"]["recaptcha"] = False
        header_disabled = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )
        self.assertNotIn("https://www.google.com", header_disabled)

    def test_build_csp_header_frame_ancestors(self):
        """
        frame-ancestors should include the wildcarded SLD+TLD when
        'desktop' is enabled, and omit it when disabled.
        """
        # Ensure feature enabled and domain set
        self.apps["app1"]["features"]["desktop"] = True
        # simulate a subdomain for the application
        self.domains["web-app-desktop"] = ["domain-example.com"]

        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")
        # Expect 'domain-example.com' in the frame-ancestors directive
        self.assertRegex(header, r"frame-ancestors\s+'self'\s+domain-example\.com;")

        # Now disable the feature and rebuild
        self.apps["app1"]["features"]["desktop"] = False
        header_no = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )
        # Should no longer contain the SLD+TLD
        self.assertNotIn("domain-example.com", header_no)

    def test_flags_default_unsafe_inline_for_styles(self):
        """
        get_csp_flags should default to include 'unsafe-inline' for style-src and style-src-elem,
        even when no explicit flags are configured.
        """
        # No explicit flags for app2
        self.assertIn(
            "'unsafe-inline'", self.filter.get_csp_flags(self.apps, "app2", "style-src")
        )
        self.assertIn(
            "'unsafe-inline'",
            self.filter.get_csp_flags(self.apps, "app2", "style-src-elem"),
        )

        # Non-style directive should NOT get unsafe-inline by default
        self.assertNotIn(
            "'unsafe-inline'",
            self.filter.get_csp_flags(self.apps, "app2", "script-src"),
        )

    def test_style_src_hashes_suppressed_by_default(self):
        """
        Because 'unsafe-inline' is defaulted for style-src, hashes for style-src should NOT be included.
        """
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")
        style_hash = self.filter.get_csp_hash("body { background: #fff; }")
        self.assertNotIn(style_hash, header)

        # Ensure 'unsafe-inline' actually present in style-src directive
        tokens = self._get_directive_tokens(header, "style-src")
        self.assertIn("'unsafe-inline'", tokens)

    def test_style_src_override_disables_inline_and_enables_hashes(self):
        """
        If an app explicitly disables 'unsafe-inline' for style-src, then hashes MUST appear.
        """
        # Configure override: disable unsafe-inline for style-src
        self.apps.setdefault("app1", {}).setdefault("server", {}).setdefault(
            "csp", {}
        ).setdefault("flags", {}).setdefault("style-src", {})
        self.apps["app1"]["server"]["csp"]["flags"]["style-src"]["unsafe-inline"] = (
            False
        )

        # Also ensure there is a style-src hash to include
        self.apps["app1"]["server"]["csp"]["hashes"]["style-src"] = (
            "body { background: #fff; }"
        )

        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")

        # Then the style hash SHOULD be present
        style_hash = self.filter.get_csp_hash("body { background: #fff; }")
        self.assertIn(style_hash, header)

        # And 'unsafe-inline' should NOT be present in style-src tokens
        tokens = self._get_directive_tokens(header, "style-src")
        self.assertNotIn("'unsafe-inline'", tokens)

    def test_style_src_elem_default_unsafe_inline(self):
        """
        style-src-elem should include 'unsafe-inline' by default (from get_csp_flags defaults).
        """
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")
        tokens = self._get_directive_tokens(header, "style-src-elem")
        self.assertIn("'unsafe-inline'", tokens)

    def test_script_src_hash_behavior_depends_on_unsafe_inline_flag(self):
        """
        For script-src:
        - When unsafe-inline=False (as in app1), hashes SHOULD be included.
        - If we flip unsafe-inline=True, hashes should NOT be included.
        """
        # Baseline (from setUp): app1 script-src has unsafe-inline=False and one hash
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")
        script_hash = self.filter.get_csp_hash("console.log('hello');")
        self.assertIn(script_hash, header)

        # Now toggle unsafe-inline=True and ensure hash disappears
        self.apps["app1"]["server"]["csp"]["flags"]["script-src"]["unsafe-inline"] = (
            True
        )
        header_inline = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )
        self.assertNotIn(script_hash, header_inline)

        # And 'unsafe-inline' should be present in the script-src tokens now
        tokens = self._get_directive_tokens(header_inline, "script-src")
        self.assertIn("'unsafe-inline'", tokens)

    def test_hashes_guard_checks_final_tokens_not_only_flags(self):
        """
        Ensure the 'no-hash-when-unsafe-inline' rule is driven by FINAL tokens,
        not just raw flags: simulate default-provided 'unsafe-inline' (style-src)
        without explicitly setting it in flags and verify hashes are still suppressed.
        """
        # Remove explicit style-src flags entirely to rely solely on defaults
        self.apps["app1"]["server"]["csp"]["flags"].pop("style-src", None)

        # Provide a style-src hash
        self.apps["app1"]["server"]["csp"]["hashes"]["style-src"] = (
            "body { color: blue; }"
        )
        style_hash = self.filter.get_csp_hash("body { color: blue; }")

        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")

        # Because defaults include 'unsafe-inline' for style-src, the hash MUST NOT appear
        self.assertNotIn(style_hash, header)

        # And 'unsafe-inline' must appear in final tokens
        tokens = self._get_directive_tokens(header, "style-src")
        self.assertIn("'unsafe-inline'", tokens)

    def test_style_family_union_flows_into_base_only_no_mirror_back(self):
        """
        Sources allowed only in style-src-elem/attr must appear in style-src (CSP2/Safari fallback),
        but we do NOT mirror back base→elem/attr.
        """
        apps = copy.deepcopy(self.apps)

        # Add distinct sources to elem and attr only
        apps["app1"]["server"]["csp"].setdefault("whitelist", {})
        apps["app1"]["server"]["csp"]["whitelist"]["style-src-elem"] = [
            "https://elem-only.example.com"
        ]
        apps["app1"]["server"]["csp"]["whitelist"]["style-src-attr"] = [
            "https://attr-only.example.com"
        ]

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")

        base_tokens = self._get_directive_tokens(header, "style-src")
        elem_tokens = self._get_directive_tokens(header, "style-src-elem")
        attr_tokens = self._get_directive_tokens(header, "style-src-attr")

        # Base must include both elem/attr sources
        self.assertIn("https://elem-only.example.com", base_tokens)
        self.assertIn("https://attr-only.example.com", base_tokens)

        # elem keeps its own sources; we did not force-copy base back into elem/attr
        # (No strict negative assertion here; just verify elem retains its own source)
        self.assertIn("https://elem-only.example.com", elem_tokens)
        self.assertIn("https://attr-only.example.com", attr_tokens)

    def test_style_explicit_disable_inline_on_base_survives_union(self):
        """
        If style-src.unsafe-inline is explicitly set to False on the base,
        it must be removed from the merged base even if elem/attr include it by default.
        """
        apps = copy.deepcopy(self.apps)
        # Explicitly disable unsafe-inline for the base
        apps["app1"].setdefault("server", {}).setdefault("csp", {}).setdefault(
            "flags", {}
        ).setdefault("style-src", {})
        apps["app1"]["server"]["csp"]["flags"]["style-src"]["unsafe-inline"] = False

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")

        base_tokens = self._get_directive_tokens(header, "style-src")
        elem_tokens = self._get_directive_tokens(header, "style-src-elem")
        attr_tokens = self._get_directive_tokens(header, "style-src-attr")

        # Base must NOT have 'unsafe-inline'
        self.assertNotIn("'unsafe-inline'", base_tokens)

        # elem/attr may still have 'unsafe-inline' by default (granularity preserved)
        self.assertIn("'unsafe-inline'", elem_tokens)
        self.assertIn("'unsafe-inline'", attr_tokens)

    def test_script_explicit_disable_inline_on_base_survives_union(self):
        """
        If script-src.unsafe-inline is explicitly set to False (default anyway),
        ensure the base remains without 'unsafe-inline' even if elem/attr enable it.
        """
        apps = copy.deepcopy(self.apps)

        # Force elem/attr to allow unsafe-inline explicitly
        apps["app1"].setdefault("server", {}).setdefault("csp", {}).setdefault(
            "flags", {}
        )
        apps["app1"]["server"]["csp"]["flags"]["script-src-elem"] = {
            "unsafe-inline": True
        }
        apps["app1"]["server"]["csp"]["flags"]["script-src-attr"] = {
            "unsafe-inline": True
        }

        # Explicitly disable on base (redundant but makes intent clear)
        apps["app1"]["server"]["csp"]["flags"]["script-src"] = {
            "unsafe-inline": False,
            "unsafe-eval": True,
        }

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")

        base_tokens = self._get_directive_tokens(header, "script-src")
        elem_tokens = self._get_directive_tokens(header, "script-src-elem")
        attr_tokens = self._get_directive_tokens(header, "script-src-attr")

        # Base: no 'unsafe-inline'
        self.assertNotIn("'unsafe-inline'", base_tokens)
        # But elem/attr: yes
        self.assertIn("'unsafe-inline'", elem_tokens)
        self.assertIn("'unsafe-inline'", attr_tokens)

        # Also ensure 'unsafe-eval' remains present on the base
        self.assertIn("'unsafe-eval'", base_tokens)

    def test_script_family_union_includes_elem_attr_hosts_in_base(self):
        """
        Hosts present only under script-src-elem/attr must appear in script-src (base).
        """
        apps = copy.deepcopy(self.apps)
        apps["app1"]["server"]["csp"].setdefault("whitelist", {})
        apps["app1"]["server"]["csp"]["whitelist"]["script-src-elem"] = [
            "https://elem-scripts.example.com"
        ]
        apps["app1"]["server"]["csp"]["whitelist"]["script-src-attr"] = [
            "https://attr-scripts.example.com"
        ]

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")

        base_tokens = self._get_directive_tokens(header, "script-src")
        self.assertIn("https://elem-scripts.example.com", base_tokens)
        self.assertIn("https://attr-scripts.example.com", base_tokens)

    def test_hash_inclusion_uses_final_base_tokens_after_union(self):
        """
        Ensure hash inclusion for style-src is evaluated after family union & explicit-disable logic.
        If base ends up WITHOUT 'unsafe-inline' after union, hashes must be present.
        """
        apps = copy.deepcopy(self.apps)

        # Explicitly disable 'unsafe-inline' on base 'style-src' so hashes can be included
        apps["app1"].setdefault("server", {}).setdefault("csp", {}).setdefault(
            "flags", {}
        ).setdefault("style-src", {})
        apps["app1"]["server"]["csp"]["flags"]["style-src"]["unsafe-inline"] = False

        # Provide a style-src hash
        content = "body { background: #abc; }"
        apps["app1"]["server"]["csp"].setdefault("hashes", {})["style-src"] = content
        expected_hash = self.filter.get_csp_hash(content)

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")
        base_tokens = self._get_directive_tokens(header, "style-src")

        self.assertNotIn("'unsafe-inline'", base_tokens)  # confirm no unsafe-inline
        self.assertIn(expected_hash, header)  # hash must be present

    def test_no_unintended_mirroring_back_to_elem_attr(self):
        """
        Verify that we do not mirror base tokens back into elem/attr:
        add a base-only host and ensure elem/attr don't automatically get it.
        """
        apps = copy.deepcopy(self.apps)
        apps["app1"]["server"]["csp"].setdefault("whitelist", {})
        # Add a base-only host
        apps["app1"]["server"]["csp"]["whitelist"]["style-src"] = [
            "https://base-only.example.com"
        ]

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")

        base_tokens = self._get_directive_tokens(header, "style-src")
        elem_tokens = self._get_directive_tokens(header, "style-src-elem")
        attr_tokens = self._get_directive_tokens(header, "style-src-attr")

        self.assertIn("https://base-only.example.com", base_tokens)
        # Not strictly required to assert negatives, but this ensures "no mirror back":
        self.assertNotIn("https://base-only.example.com", elem_tokens)
        self.assertNotIn("https://base-only.example.com", attr_tokens)

    def test_logout_does_not_add_unsafe_inline_when_disabled(self):
        """
        When the logout feature is NOT enabled, the filter must NOT
        inject 'unsafe-inline' into script-src-attr or script-src-elem.
        """
        header = self.filter.build_csp_header(self.apps, "app1", self.domains, "https")

        attr_tokens = self._get_directive_tokens(header, "script-src-attr")
        elem_tokens = self._get_directive_tokens(header, "script-src-elem")

        self.assertNotIn("'unsafe-inline'", attr_tokens)
        self.assertNotIn("'unsafe-inline'", elem_tokens)

    def test_logout_adds_unsafe_inline_to_script_attr_and_elem(self):
        """
        When the logout feature IS enabled, script-src-attr and script-src-elem
        must automatically include 'unsafe-inline' to support inline event handlers.
        """
        apps = copy.deepcopy(self.apps)
        domains = copy.deepcopy(self.domains)

        apps["app1"].setdefault("features", {})["logout"] = True
        domains["web-svc-logout"] = ["logout.example.org"]
        domains["web-app-keycloak"] = ["keycloak.example.org"]

        header = self.filter.build_csp_header(apps, "app1", domains, "https")

        attr_tokens = self._get_directive_tokens(header, "script-src-attr")
        elem_tokens = self._get_directive_tokens(header, "script-src-elem")

        self.assertIn("'unsafe-inline'", attr_tokens)
        self.assertIn("'unsafe-inline'", elem_tokens)

    def test_logout_respects_explicit_disable_on_base_script_src(self):
        """
        Even if logout adds 'unsafe-inline' to attr/elem, an explicit
        unsafe-inline=False on script-src MUST be respected and must not be overridden.
        """
        apps = copy.deepcopy(self.apps)
        domains = copy.deepcopy(self.domains)

        apps["app1"].setdefault("server", {}).setdefault("csp", {}).setdefault(
            "flags", {}
        )
        apps["app1"]["server"]["csp"]["flags"]["script-src"] = {
            "unsafe-inline": False,
            "unsafe-eval": True,
        }

        apps["app1"].setdefault("features", {})["logout"] = True
        domains["web-svc-logout"] = ["logout.example.org"]
        domains["web-app-keycloak"] = ["keycloak.example.org"]

        header = self.filter.build_csp_header(apps, "app1", domains, "https")

        base_tokens = self._get_directive_tokens(header, "script-src")
        attr_tokens = self._get_directive_tokens(header, "script-src-attr")
        elem_tokens = self._get_directive_tokens(header, "script-src-elem")

        # Base MUST remain strict
        self.assertNotIn("'unsafe-inline'", base_tokens)
        # Attr/elem MUST stay relaxed
        self.assertIn("'unsafe-inline'", attr_tokens)
        self.assertIn("'unsafe-inline'", elem_tokens)

    def test_logout_propagates_unsafe_inline_into_base_when_not_explicitly_disabled(
        self,
    ):
        """
        When logout enables unsafe-inline for script-src-attr/-elem
        AND script-src does NOT explicitly disable unsafe-inline,
        then family union must inject 'unsafe-inline' into script-src.
        """
        apps = copy.deepcopy(self.apps)
        domains = copy.deepcopy(self.domains)

        # Base does NOT explicitly disable unsafe-inline
        apps["app1"].setdefault("server", {}).setdefault("csp", {}).setdefault(
            "flags", {}
        )
        apps["app1"]["server"]["csp"]["flags"]["script-src"] = {"unsafe-eval": True}

        apps["app1"]["features"]["logout"] = True
        domains["web-svc-logout"] = ["logout.example.org"]
        domains["web-app-keycloak"] = ["keycloak.example.org"]

        header = self.filter.build_csp_header(apps, "app1", domains, "https")

        base_tokens = self._get_directive_tokens(header, "script-src")
        attr_tokens = self._get_directive_tokens(header, "script-src-attr")
        elem_tokens = self._get_directive_tokens(header, "script-src-elem")

        # All three must contain 'unsafe-inline'
        self.assertIn("'unsafe-inline'", base_tokens)
        self.assertIn("'unsafe-inline'", attr_tokens)
        self.assertIn("'unsafe-inline'", elem_tokens)

    def test_build_csp_header_hcaptcha_toggle(self):
        """
        When the 'hcaptcha' feature is enabled, the CSP must include
        the hCaptcha script and frame hosts. When disabled, they must
        not appear in any directive.
        """
        # enabled case
        self.apps["app1"].setdefault("features", {})["hcaptcha"] = True
        header_enabled = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )

        # script-src-elem must contain hCaptcha hosts
        script_elem_tokens = self._get_directive_tokens(
            header_enabled, "script-src-elem"
        )
        self.assertIn("https://www.hcaptcha.com", script_elem_tokens)
        self.assertIn("https://js.hcaptcha.com", script_elem_tokens)

        # base script-src must also include them (family union)
        script_base_tokens = self._get_directive_tokens(header_enabled, "script-src")
        self.assertIn("https://www.hcaptcha.com", script_base_tokens)
        self.assertIn("https://js.hcaptcha.com", script_base_tokens)

        # frame-src must contain the hCaptcha assets host
        frame_tokens = self._get_directive_tokens(header_enabled, "frame-src")
        self.assertIn("https://newassets.hcaptcha.com/", frame_tokens)

        # disabled case
        self.apps["app1"]["features"]["hcaptcha"] = False
        header_disabled = self.filter.build_csp_header(
            self.apps, "app1", self.domains, "https"
        )

        for directive in ("script-src", "script-src-elem", "frame-src"):
            tokens = self._get_directive_tokens(header_disabled, directive)
            self.assertNotIn("https://www.hcaptcha.com", tokens)
            self.assertNotIn("https://js.hcaptcha.com", tokens)
            self.assertNotIn("https://newassets.hcaptcha.com/", tokens)

    def test_connect_src_tokens_are_sorted_and_self_first(self):
        """
        Tokens inside connect-src must be deterministically sorted with 'self' first.
        This ensures stable CSP output and avoids fake Ansible changes.
        """
        apps = copy.deepcopy(self.apps)

        # Provide an unsorted whitelist for connect-src
        apps["app1"]["server"]["csp"].setdefault("whitelist", {})
        apps["app1"]["server"]["csp"]["whitelist"]["connect-src"] = [
            "https://zzz.example.com",
            "https://aaa.example.com",
            "https://mmm.example.com",
        ]

        header = self.filter.build_csp_header(apps, "app1", self.domains, "https")
        tokens = self._get_directive_tokens(header, "connect-src")

        # Ensure we actually have tokens
        self.assertGreater(len(tokens), 0)

        # 'self' must be first if present
        self.assertEqual(tokens[0], "'self'")

        # All remaining tokens must be sorted lexicographically
        tail = tokens[1:]
        self.assertEqual(tail, sorted(tail))

    def test_connect_src_header_deterministic_for_unsorted_whitelist(self):
        """
        Two apps with the same connect-src whitelist in different orders must
        produce identical CSP headers. This verifies deterministic sorting.
        """
        apps1 = copy.deepcopy(self.apps)
        apps2 = copy.deepcopy(self.apps)

        apps1["app1"]["server"]["csp"].setdefault("whitelist", {})
        apps2["app1"]["server"]["csp"].setdefault("whitelist", {})

        # Same items, different order
        apps1["app1"]["server"]["csp"]["whitelist"]["connect-src"] = [
            "https://c.example.com",
            "https://b.example.com",
            "https://a.example.com",
        ]
        apps2["app1"]["server"]["csp"]["whitelist"]["connect-src"] = [
            "https://a.example.com",
            "https://c.example.com",
            "https://b.example.com",
        ]

        header1 = self.filter.build_csp_header(apps1, "app1", self.domains, "https")
        header2 = self.filter.build_csp_header(apps2, "app1", self.domains, "https")

        self.assertEqual(header1, header2)


if __name__ == "__main__":
    unittest.main()
