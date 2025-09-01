from ansible.errors import AnsibleFilterError
import hashlib
import base64
import sys
import os

# Ensure module_utils is importable when this filter runs from Ansible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.config_utils import get_app_conf
from module_utils.get_url import get_url


class FilterModule(object):
    """
    Custom filters for Content Security Policy generation and CSP-related utilities.
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
        Default: 'unsafe-inline' is enabled for style-src and style-src-elem.
        """
        # Defaults that apply to all apps
        default_flags = {}
        if directive in ('style-src', 'style-src-elem'):
            default_flags = {'unsafe-inline': True}

        configured = get_app_conf(
            applications,
            application_id,
            'server.csp.flags.' + directive,
            False,
            {}
        )

        # Merge defaults with configured flags (configured overrides defaults)
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
        - Flags (e.g., 'unsafe-eval', 'unsafe-inline') are read from server.csp.flags.<directive>,
          with sane defaults applied in get_csp_flags (always 'unsafe-inline' for style-src and style-src-elem).
        - Inline hashes are read from server.csp.hashes.<directive>.
        - Whitelists are read from server.csp.whitelist.<directive>.
        - Inline hashes are added only if the final tokens do NOT include 'unsafe-inline'.
        """
        try:
            directives = [
                'default-src',      # Fallback source list for content types not explicitly listed
                'connect-src',      # Allowed URLs for XHR, WebSockets, EventSource, fetch()
                'frame-ancestors',  # Who may embed this page
                'frame-src',        # Sources for nested browsing contexts (e.g., <iframe>)
                'script-src',       # Sources for script execution
                'script-src-elem',  # Sources for <script> elements
                'style-src',        # Sources for inline styles and <style>/<link> elements
                'style-src-elem',   # Sources for <style> and <link rel="stylesheet">
                'font-src',         # Sources for fonts
                'worker-src',       # Sources for workers
                'manifest-src',     # Sources for web app manifests
                'media-src',        # Sources for audio and video
            ]

            parts = []

            for directive in directives:
                tokens = ["'self'"]

                # 1) Load flags (includes defaults from get_csp_flags)
                flags = self.get_csp_flags(applications, application_id, directive)
                tokens += flags

                # 2) Allow fetching from internal CDN by default for selected directives
                if directive in ['script-src-elem', 'connect-src', 'style-src-elem']:
                    tokens.append(get_url(domains, 'web-svc-cdn', web_protocol))

                # 3) Matomo integration if feature is enabled
                if directive in ['script-src-elem', 'connect-src']:
                    if self.is_feature_enabled(applications, matomo_feature_name, application_id):
                        tokens.append(get_url(domains, 'web-app-matomo', web_protocol))

                # 4) ReCaptcha integration (scripts + frames) if feature is enabled
                if self.is_feature_enabled(applications, 'recaptcha', application_id):
                    if directive in ['script-src-elem', 'frame-src']:
                        tokens.append('https://www.gstatic.com')
                        tokens.append('https://www.google.com')

                # 5) Frame ancestors handling (desktop + logout support)
                if directive == 'frame-ancestors':
                    if self.is_feature_enabled(applications, 'desktop', application_id):
                        # Allow being embedded by the desktop app domain (and potentially its parent)
                        domain = domains.get('web-app-desktop')[0]
                        sld_tld = ".".join(domain.split(".")[-2:])  # e.g., example.com
                        tokens.append(f"{sld_tld}")
                    if self.is_feature_enabled(applications, 'logout', application_id):
                        # Allow embedding via logout proxy and Keycloak app
                        tokens.append(get_url(domains, 'web-svc-logout', web_protocol))
                        tokens.append(get_url(domains, 'web-app-keycloak', web_protocol))

                # 6) Custom whitelist entries
                tokens += self.get_csp_whitelist(applications, application_id, directive)

                # 7) Add inline content hashes ONLY if final tokens do NOT include 'unsafe-inline'
                #    (Check tokens, not flags, to include defaults and later modifications.)
                if "'unsafe-inline'" not in tokens:
                    for snippet in self.get_csp_inline_content(applications, application_id, directive):
                        tokens.append(self.get_csp_hash(snippet))

                # Append directive
                parts.append(f"{directive} {' '.join(tokens)};")

            # 8) Static img-src directive (kept permissive for data/blob and any host)
            parts.append("img-src * data: blob:;")

            return ' '.join(parts)

        except Exception as exc:
            raise AnsibleFilterError(f"build_csp_header failed: {exc}")
