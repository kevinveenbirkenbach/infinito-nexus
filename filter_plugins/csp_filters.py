from ansible.errors import AnsibleFilterError
import hashlib
import base64
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.config_utils import get_app_conf

class FilterModule(object):
    """
    Custom filters for Content Security Policy generation and CSP-related utilities.
    """

    def filters(self):
        return {
            'build_csp_header': self.build_csp_header,
        }

    @staticmethod
    def is_feature_enabled(applications: dict, feature: str, application_id: str) -> bool:
        """
        Return True if applications[application_id].features[feature] is truthy.
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
        Dynamically extract all CSP flags for a given directive and return them as tokens,
        e.g., "'unsafe-eval'", "'unsafe-inline'", etc.
        """
        flags = get_app_conf(
            applications,
            application_id,
            'server.csp.flags.' + directive,
            False,
            {}
        )
        tokens = []

        for flag_name, enabled in flags.items():
            if enabled:
                tokens.append(f"'{flag_name}'")

        return tokens

    @staticmethod
    def get_csp_inline_content(applications, application_id, directive):
        """
        Return inline script/style snippets to hash for a given CSP directive.
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
        Compute the SHA256 hash of the given inline content and return
        a CSP token like "'sha256-<base64>'".
        """
        try:
            digest = hashlib.sha256(content.encode('utf-8')).digest()
            b64 = base64.b64encode(digest).decode('utf-8')
            return f"'sha256-{b64}'"
        except Exception as exc:
            raise AnsibleFilterError(f"get_csp_hash failed: {exc}")

    def build_csp_header(
        self,
        applications,
        application_id,
        domains,
        web_protocol='https',
        matomo_feature_name='matomo'
    ):
        """
        Build the Content-Security-Policy header value dynamically based on application settings.
        Inline hashes are read from applications[application_id].csp.hashes
        """
        try:
            directives = [
                'default-src',
                'connect-src',
                'frame-ancestors',
                'frame-src',
                'script-src',
                'script-src-elem',
                'style-src',
                'font-src',
                'worker-src',
                'manifest-src',
                'media-src',
            ]
            parts = []

            for directive in directives:
                tokens = ["'self'"]

                # unsafe-eval / unsafe-inline flags
                flags = self.get_csp_flags(applications, application_id, directive)
                tokens += flags

                # Matomo integration
                if (
                    self.is_feature_enabled(applications, matomo_feature_name, application_id)
                    and directive in ['script-src-elem', 'connect-src']
                ):
                    matomo_domain = domains.get('web-app-matomo')[0]
                    if matomo_domain:
                        tokens.append(f"{web_protocol}://{matomo_domain}")

                # ReCaptcha integration: allow loading scripts from Google if feature enabled
                if self.is_feature_enabled(applications, 'recaptcha', application_id):
                    if directive in ['script-src-elem',"frame-src"]:
                        tokens.append('https://www.gstatic.com')
                        tokens.append('https://www.google.com')

                # Allow the loading of js from the cdn
                if directive == 'script-src-elem':
                    if self.is_feature_enabled(applications, 'logout', application_id) or self.is_feature_enabled(applications, 'port-ui-desktop', application_id):
                        domain = domains.get('web-svc-cdn')[0]
                        tokens.append(f"{domain}")

                if directive == 'frame-ancestors':
                    # Enable loading via ancestors
                    if self.is_feature_enabled(applications, 'port-ui-desktop', application_id):
                        domain = domains.get('web-app-port-ui')[0]
                        sld_tld = ".".join(domain.split(".")[-2:])  # yields "example.com"
                        tokens.append(f"{sld_tld}")                 # yields "*.example.com"
                
                    if self.is_feature_enabled(applications, 'logout', application_id):
                        
                        # Allow logout via infinito logout proxy
                        domain = domains.get('web-svc-logout')[0] 
                        tokens.append(f"{domain}") 
                        
                        # Allow logout via keycloak app
                        domain = domains.get('web-app-keycloak')[0]
                        tokens.append(f"{domain}") 
                        
                # whitelist
                tokens += self.get_csp_whitelist(applications, application_id, directive)

                # only add hashes if 'unsafe-inline' is NOT in flags
                if "'unsafe-inline'" not in flags:
                    for snippet in self.get_csp_inline_content(applications, application_id, directive):
                        tokens.append(self.get_csp_hash(snippet))

                parts.append(f"{directive} {' '.join(tokens)};")

            # static img-src
            parts.append("img-src * data: blob:;")
            return ' '.join(parts)

        except Exception as exc:
            raise AnsibleFilterError(f"build_csp_header failed: {exc}")
