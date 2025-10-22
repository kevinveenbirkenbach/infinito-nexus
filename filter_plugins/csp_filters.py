from ansible.errors import AnsibleFilterError
import hashlib
import base64
import sys
import os

# Ensure module_utils is importable when this filter runs from Ansible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.config_utils import get_app_conf
from module_utils.get_url import get_url


def _dedup_preserve(seq):
    """Return a list with stable order and unique items."""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


class FilterModule(object):
    """
    Jinja filters for building a robust, CSP3-aware Content-Security-Policy header.
    Safari/CSP2 compatibility is ensured by merging the -elem/-attr variants into the base
    directives (style-src, script-src). We intentionally do NOT mirror back into -elem/-attr
    to allow true CSP3 granularity on modern browsers.
    """

    def filters(self):
        return {
            'build_csp_header': self.build_csp_header,
        }

    # -------------------------------
    # Helpers
    # -------------------------------

    @staticmethod
    def is_feature_enabled(applications: dict, feature: str, application_id: str) -> bool:
        """
        Returns True if applications[application_id].features[feature] is truthy.
        """
        return get_app_conf(
            applications,
            application_id,
            'features.' + feature,
            False,
            False
        )

    @staticmethod
    def get_csp_whitelist(applications, application_id, directive):
        """
        Returns a list of additional whitelist entries for a given directive.
        Accepts both scalar and list in config; always returns a list.
        """
        wl = get_app_conf(
            applications,
            application_id,
            'server.csp.whitelist.' + directive,
            False,
            []
        )
        if isinstance(wl, list):
            return wl
        if wl:
            return [wl]
        return []

    @staticmethod
    def get_csp_flags(applications, application_id, directive):
        """
        Returns CSP flag tokens (e.g., "'unsafe-eval'", "'unsafe-inline'") for a directive,
        merging sane defaults with app config.

        Defaults:
          - For styles we enable 'unsafe-inline' by default (style-src, style-src-elem, style-src-attr),
            because many apps rely on inline styles / style attributes.
          - For scripts we do NOT enable 'unsafe-inline' by default.
        """
        default_flags = {}
        if directive in ('style-src', 'style-src-elem', 'style-src-attr'):
            default_flags = {'unsafe-inline': True}

        configured = get_app_conf(
            applications,
            application_id,
            'server.csp.flags.' + directive,
            False,
            {}
        )

        merged = {**default_flags, **configured}

        tokens = []
        for flag_name, enabled in merged.items():
            if enabled:
                tokens.append(f"'{flag_name}'")
        return tokens

    @staticmethod
    def get_csp_inline_content(applications, application_id, directive):
        """
        Returns inline script/style snippets to hash for a given directive.
        Accepts both scalar and list in config; always returns a list.
        """
        snippets = get_app_conf(
            applications,
            application_id,
            'server.csp.hashes.' + directive,
            False,
            []
        )
        if isinstance(snippets, list):
            return snippets
        if snippets:
            return [snippets]
        return []

    @staticmethod
    def get_csp_hash(content):
        """
        Computes the SHA256 hash of the given inline content and returns
        a CSP token like "'sha256-<base64>'".
        """
        try:
            digest = hashlib.sha256(content.encode('utf-8')).digest()
            b64 = base64.b64encode(digest).decode('utf-8')
            return f"'sha256-{b64}'"
        except Exception as exc:
            raise AnsibleFilterError(f"get_csp_hash failed: {exc}")

    # -------------------------------
    # Main builder
    # -------------------------------

    def build_csp_header(
        self,
        applications,
        application_id,
        domains,
        web_protocol='https',
        matomo_feature_name='matomo'
    ):
        """
        Builds the Content-Security-Policy header value dynamically based on application settings.

        Key points:
          - CSP3-aware: supports base/elem/attr for styles and scripts.
          - Safari/CSP2 fallback: base directives (style-src, script-src) always include
            the union of their -elem/-attr variants.
          - We do NOT mirror back into -elem/-attr; finer CSP3 rules remain effective
            on modern browsers if you choose to use them.
          - If the app explicitly disables a token on the *base* (e.g. style-src.unsafe-inline: false),
            that token is removed from the merged base even if present in elem/attr.
          - Inline hashes are added ONLY if that directive does NOT include 'unsafe-inline'.
          - Whitelists/flags/hashes read from:
              server.csp.whitelist.<directive>
              server.csp.flags.<directive>
              server.csp.hashes.<directive>
          - “Smart defaults”:
              * internal CDN for style/script elem and connect
              * Matomo endpoints (if feature enabled) for script-elem/connect
              * Simpleicons (if feature enabled) for connect
              * reCAPTCHA (if feature enabled) for script-elem/frame-src
              * frame-ancestors extended for desktop/logout/keycloak if enabled
        """
        try:
            directives = [
                'default-src',
                'connect-src',
                'frame-ancestors',
                'frame-src',
                'script-src',
                'script-src-elem',
                'script-src-attr',
                'style-src',
                'style-src-elem',
                'style-src-attr',
                'font-src',
                'worker-src',
                'manifest-src',
                'media-src',
            ]

            tokens_by_dir = {}
            explicit_flags_by_dir = {}

            for directive in directives:
                # Collect explicit flags (to later respect explicit "False" on base during merge)
                explicit_flags = get_app_conf(
                    applications,
                    application_id,
                    'server.csp.flags.' + directive,
                    False,
                    {}
                )
                explicit_flags_by_dir[directive] = explicit_flags

                tokens = ["'self'"]

                # 1) Flags (with sane defaults)
                flags = self.get_csp_flags(applications, application_id, directive)
                tokens += flags

                # 2) Internal CDN defaults for selected directives
                if directive in ('script-src-elem', 'connect-src', 'style-src-elem', 'style-src'):
                    tokens.append(get_url(domains, 'web-svc-cdn', web_protocol))

                # 3) Matomo (if enabled)
                if directive in ('script-src-elem', 'connect-src'):
                    if self.is_feature_enabled(applications, matomo_feature_name, application_id):
                        tokens.append(get_url(domains, 'web-app-matomo', web_protocol))

                # 4) Simpleicons (if enabled) – typically used via connect-src (fetch)
                if directive == 'connect-src':
                    if self.is_feature_enabled(applications, 'simpleicons', application_id):
                        tokens.append(get_url(domains, 'web-svc-simpleicons', web_protocol))

                # 5) reCAPTCHA (if enabled) – scripts + frames
                if self.is_feature_enabled(applications, 'recaptcha', application_id):
                    if directive in ('script-src-elem', 'frame-src'):
                        tokens.append('https://www.gstatic.com')
                        tokens.append('https://www.google.com')

                # 6) Frame ancestors (desktop + logout)
                if directive == 'frame-ancestors':
                    if self.is_feature_enabled(applications, 'desktop', application_id):
                        # Allow being embedded by the desktop app domain's site
                        domain = domains.get('web-app-desktop')[0]
                        sld_tld = ".".join(domain.split(".")[-2:])  # e.g., example.com
                        tokens.append(f"{sld_tld}")
                    if self.is_feature_enabled(applications, 'logout', application_id):
                        tokens.append(get_url(domains, 'web-svc-logout', web_protocol))
                        tokens.append(get_url(domains, 'web-app-keycloak', web_protocol))

                # 7) Custom whitelist
                tokens += self.get_csp_whitelist(applications, application_id, directive)

                # 8) Inline hashes (only if this directive does NOT include 'unsafe-inline')
                if "'unsafe-inline'" not in tokens:
                    for snippet in self.get_csp_inline_content(applications, application_id, directive):
                        tokens.append(self.get_csp_hash(snippet))

                tokens_by_dir[directive] = _dedup_preserve(tokens)

            # ----------------------------------------------------------
            # CSP3 families → ensure CSP2 fallback (Safari-safe)
            # Merge style/script families so base contains union of elem/attr.
            # Respect explicit disables on the base (e.g. unsafe-inline=False).
            # Do NOT mirror back into elem/attr (keep granularity).
            # ----------------------------------------------------------
            def _strip_if_disabled(unioned_tokens, explicit_flags, name):
                """
                Remove a token (e.g. 'unsafe-inline') from the unioned token list
                if it is explicitly disabled in the base directive flags.
                """
                if isinstance(explicit_flags, dict) and explicit_flags.get(name) is False:
                    tok = f"'{name}'"
                    return [t for t in unioned_tokens if t != tok]
                return unioned_tokens

            def merge_family(base_key, elem_key, attr_key):
                base = tokens_by_dir.get(base_key, [])
                elem = tokens_by_dir.get(elem_key, [])
                attr = tokens_by_dir.get(attr_key, [])
                union = _dedup_preserve(base + elem + attr)

                # Respect explicit disables on the base
                explicit_base = explicit_flags_by_dir.get(base_key, {})
                # The most relevant flags for script/style:
                for flag_name in ('unsafe-inline', 'unsafe-eval'):
                    union = _strip_if_disabled(union, explicit_base, flag_name)

                tokens_by_dir[base_key] = union  # write back only to base

            merge_family('style-src',  'style-src-elem',  'style-src-attr')
            merge_family('script-src', 'script-src-elem', 'script-src-attr')

            # ----------------------------------------------------------
            # Assemble header
            # ----------------------------------------------------------
            parts = []
            for directive in directives:
                if directive in tokens_by_dir:
                    parts.append(f"{directive} {' '.join(tokens_by_dir[directive])};")

            # Keep permissive img-src for data/blob + any host (as before)
            parts.append("img-src * data: blob:;")

            return ' '.join(parts)

        except Exception as exc:
            raise AnsibleFilterError(f"build_csp_header failed: {exc}")
