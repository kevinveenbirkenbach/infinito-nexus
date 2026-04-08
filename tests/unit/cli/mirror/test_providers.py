from __future__ import annotations

import os
import unittest
import urllib.error
from unittest.mock import patch

from cli.mirror.model import ImageRef
from cli.mirror.providers import GHCRProvider


class _DummyResponse:
    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class TestGHCRProviderSetPublic(unittest.TestCase):
    def setUp(self) -> None:
        self.image = ImageRef(
            role="web-app-nextcloud",
            service="app",
            name="nextcloud",
            version="31.0.0",
            source="library/nextcloud:31.0.0",
        )

    @patch.dict(os.environ, {"GITHUB_TOKEN": "secret-token"}, clear=False)
    def test_set_public_uses_user_package_endpoint(self) -> None:
        provider = GHCRProvider("kevinveenbirkenbach")
        requests: list[str] = []

        def fake_urlopen(req):
            requests.append(req.full_url)
            return _DummyResponse()

        with patch(
            "cli.mirror.providers.urllib.request.urlopen", side_effect=fake_urlopen
        ):
            provider._set_public(self.image)

        self.assertEqual(
            requests,
            [
                "https://api.github.com/users/kevinveenbirkenbach/packages/container/mirror%2Fnextcloud"
            ],
        )

    @patch.dict(os.environ, {"GITHUB_TOKEN": "secret-token"}, clear=False)
    def test_set_public_falls_back_to_org_endpoint_after_user_404(self) -> None:
        provider = GHCRProvider("acme")
        requests: list[str] = []

        def fake_urlopen(req):
            requests.append(req.full_url)
            if "/users/" in req.full_url:
                raise urllib.error.HTTPError(
                    req.full_url,
                    404,
                    "Not Found",
                    hdrs=None,
                    fp=None,
                )
            return _DummyResponse()

        with patch(
            "cli.mirror.providers.urllib.request.urlopen", side_effect=fake_urlopen
        ):
            provider._set_public(self.image)

        self.assertEqual(
            requests,
            [
                "https://api.github.com/users/acme/packages/container/mirror%2Fnextcloud",
                "https://api.github.com/orgs/acme/packages/container/mirror%2Fnextcloud",
            ],
        )

    def test_ensure_public_delegates_to_set_public(self) -> None:
        provider = GHCRProvider("acme")

        with patch.object(provider, "_set_public") as mock_set_public:
            provider.ensure_public(self.image)

        mock_set_public.assert_called_once_with(self.image)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
