from __future__ import annotations

import unittest

from ansible.errors import AnsibleError

from plugins.lookup.image import LookupModule


class TestImageLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.lookup = LookupModule()

    def test_explicit_role_id_returns_default_fields(self) -> None:
        variables = {
            "images": {
                "playwright": {
                    "image": "mcr.microsoft.com/playwright",
                    "version": "v1.58.2-noble",
                }
            }
        }

        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "image"],
                variables=variables,
            ),
            ["mcr.microsoft.com/playwright"],
        )
        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "version"],
                variables=variables,
            ),
            ["v1.58.2-noble"],
        )
        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "ref"],
                variables=variables,
            ),
            ["mcr.microsoft.com/playwright:v1.58.2-noble"],
        )

    def test_infers_role_id_from_role_name(self) -> None:
        variables = {
            "role_name": "sys-ctl-hlth-csp",
            "images": {
                "csp-checker": {
                    "image": "ghcr.io/kevinveenbirkenbach/csp-checker",
                    "version": "stable",
                }
            },
        }

        self.assertEqual(
            self.lookup.run(["csp-checker", "ref"], variables=variables),
            ["ghcr.io/kevinveenbirkenbach/csp-checker:stable"],
        )

    def test_role_name_wins_even_if_application_id_is_also_set(self) -> None:
        variables = {
            "role_name": "web-app-nextcloud",
            "application_id": "nextcloud",
            "images": {
                "helper": {
                    "image": "docker.io/acme/helper",
                    "version": "1.0.0",
                }
            },
            "images_overrides": {
                "web-app-nextcloud": {
                    "helper": {
                        "image": "ghcr.io/acme/mirror/helper",
                    }
                }
            },
        }

        self.assertEqual(
            self.lookup.run(["helper"], variables=variables),
            [
                {
                    "image": "ghcr.io/acme/mirror/helper",
                    "version": "1.0.0",
                }
            ],
        )

    def test_override_wins_fieldwise_over_defaults(self) -> None:
        variables = {
            "role_name": "test-e2e-playwright",
            "images": {
                "playwright": {
                    "image": "mcr.microsoft.com/playwright",
                    "version": "v1.58.2-noble",
                }
            },
            "images_overrides": {
                "test-e2e-playwright": {
                    "playwright": {
                        "image": "ghcr.io/acme/mirror/mcr.microsoft.com/playwright",
                    }
                }
            },
        }

        self.assertEqual(
            self.lookup.run(["playwright"], variables=variables),
            [
                {
                    "image": "ghcr.io/acme/mirror/mcr.microsoft.com/playwright",
                    "version": "v1.58.2-noble",
                }
            ],
        )

    def test_missing_mapping_raises(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["sys-ctl-hlth-csp", "csp-checker", "ref"],
                variables={"images": {}, "images_overrides": {}},
            )

    def test_implicit_lookup_requires_role_name_when_only_application_id_exists(
        self,
    ) -> None:
        variables = {
            "application_id": "web-app-nextcloud",
            "images": {
                "helper": {
                    "image": "docker.io/acme/helper",
                    "version": "1.0.0",
                }
            },
        }

        with self.assertRaises(AnsibleError) as ctx:
            self.lookup.run(["helper", "ref"], variables=variables)

        self.assertIn("set role_name or pass role_id explicitly", str(ctx.exception))

    def test_invalid_images_overrides_type_raises(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["sys-ctl-hlth-csp", "csp-checker", "ref"],
                variables={
                    "images": {},
                    "images_overrides": ["not", "a", "mapping"],
                },
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
