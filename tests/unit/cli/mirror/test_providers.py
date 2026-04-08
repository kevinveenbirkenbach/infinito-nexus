from __future__ import annotations

import unittest

from cli.mirror.model import ImageRef
from cli.mirror.providers import GHCRProvider


class TestGHCRProviderImageBase(unittest.TestCase):
    def setUp(self) -> None:
        self.image = ImageRef(
            role="web-app-nextcloud",
            service="app",
            name="nextcloud",
            version="31.0.0",
            source="library/nextcloud:31.0.0",
        )

    def test_image_base_simple(self) -> None:
        provider = GHCRProvider("acme")
        self.assertEqual(
            provider.image_base(self.image),
            "ghcr.io/acme/mirror/nextcloud",
        )

    def test_image_base_with_slash_in_name(self) -> None:
        image = ImageRef(
            role="web-app-foo",
            service="svc",
            name="foo/bar",
            version="1.0",
            source="foo/bar:1.0",
        )
        provider = GHCRProvider("acme")
        self.assertEqual(
            provider.image_base(image),
            "ghcr.io/acme/mirror/foo-bar",
        )

    def test_namespace_is_lowercased(self) -> None:
        provider = GHCRProvider("ACME")
        self.assertEqual(provider.namespace, "acme")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
