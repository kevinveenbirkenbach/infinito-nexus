import pathlib
import unittest

from utils.cache.files import read_text
from utils.roles.mapping import ROLE_FILE_VARS_MAIN


class TestDashboardOidcSpot(unittest.TestCase):
    def test_dashboard_oidc_uses_canonical_base_url(self):
        vars_content = read_text(
            str(pathlib.Path(f"roles/web-app-dashboard/{ROLE_FILE_VARS_MAIN}"))
        )
        js_content = read_text(
            str(pathlib.Path("roles/web-app-dashboard/templates/javascript/oidc.js.j2"))
        )

        self.assertIn("DASHBOARD_APP_BASE_URL", vars_content)
        self.assertIn('redirectUri: "{{ DASHBOARD_APP_BASE_URL }}"', js_content)
        self.assertIn("silentCheckSsoRedirectUri", js_content)
        self.assertNotIn("redirectUri: window.location.origin", js_content)

    def test_dashboard_playwright_matomo_flag_matches_runtime_injection_preconditions(
        self,
    ):
        content = read_text(
            str(pathlib.Path("roles/web-app-dashboard/templates/playwright.env.j2"))
        )

        self.assertIn(
            "LOGIN_PASSWORD={{ lookup('users', 'administrator').password", content
        )
        self.assertIn(
            "MATOMO_ENABLED={{ lookup('config', application_id, 'services.matomo.enabled') }}",
            content,
        )


if __name__ == "__main__":
    unittest.main()
