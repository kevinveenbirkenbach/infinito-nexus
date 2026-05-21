from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError

from plugins.lookup import image as image_lookup
from plugins.lookup.image import LookupModule
from utils.roles.mapping import ROLE_FILE_META_SERVICES


class TestImageLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.lookup = LookupModule()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        patcher = patch.object(image_lookup, "PROJECT_ROOT", self.repo_root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write_services(self, role_id: str, content: str) -> None:
        path = self.repo_root / "roles" / role_id / ROLE_FILE_META_SERVICES
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")

    def test_explicit_role_id_returns_default_fields(self) -> None:
        self._write_services(
            "test-e2e-playwright",
            """
            playwright:
              image: mcr.microsoft.com/playwright
              version: v1.58.2-noble
            """,
        )

        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "image"],
                variables={},
            ),
            ["mcr.microsoft.com/playwright"],
        )
        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "version"],
                variables={},
            ),
            ["v1.58.2-noble"],
        )
        self.assertEqual(
            self.lookup.run(
                ["test-e2e-playwright", "playwright", "ref"],
                variables={},
            ),
            ["mcr.microsoft.com/playwright:v1.58.2-noble"],
        )

    def test_inferred_role_id_form_is_rejected(self) -> None:
        # The 2-arg form (service_name, want) used to infer role_id from
        # role_name. Lazy re-evaluation of such expressions inside another
        # role's template silently resolved the wrong role; the form is now
        # rejected unconditionally so the bug class cannot reoccur.
        self._write_services(
            "sys-ctl-hlth-csp",
            """
            csp-checker:
              image: ghcr.io/kevinveenbirkenbach/csp-checker
              version: stable
            """,
        )
        with self.assertRaises(AnsibleError) as ctx:
            self.lookup.run(
                ["csp-checker", "ref"],
                variables={"role_name": "sys-ctl-hlth-csp"},
            )
        self.assertIn("role_id, service_name", str(ctx.exception))

    def test_single_arg_form_is_rejected(self) -> None:
        with self.assertRaises(AnsibleError) as ctx:
            self.lookup.run(
                ["helper"],
                variables={"role_name": "web-app-nextcloud"},
            )
        self.assertIn("role_id, service_name", str(ctx.exception))

    def test_override_wins_fieldwise_over_defaults(self) -> None:
        self._write_services(
            "test-e2e-playwright",
            """
            playwright:
              image: mcr.microsoft.com/playwright
              version: v1.58.2-noble
            """,
        )

        variables = {
            "images_overrides": {
                "test-e2e-playwright": {
                    "playwright": {
                        "image": "ghcr.io/acme/mirror/mcr.microsoft.com/playwright",
                    }
                }
            },
        }

        self.assertEqual(
            self.lookup.run(["test-e2e-playwright", "playwright"], variables=variables),
            [
                {
                    "image": "ghcr.io/acme/mirror/mcr.microsoft.com/playwright",
                    "version": "v1.58.2-noble",
                }
            ],
        )

    def test_missing_mapping_raises(self) -> None:
        self._write_services(
            "sys-ctl-hlth-csp",
            """
            csp:
              lifecycle: beta
            """,
        )
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["sys-ctl-hlth-csp", "csp-checker", "ref"],
                variables={"images_overrides": {}},
            )

    def test_missing_meta_services_file_raises(self) -> None:
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["nonexistent-role", "svc", "ref"],
                variables={},
            )

    def test_invalid_images_overrides_type_raises(self) -> None:
        self._write_services(
            "sys-ctl-hlth-csp",
            """
            csp-checker:
              image: ghcr.io/kevinveenbirkenbach/csp-checker
              version: stable
            """,
        )
        with self.assertRaises(AnsibleError):
            self.lookup.run(
                ["sys-ctl-hlth-csp", "csp-checker", "ref"],
                variables={
                    "images_overrides": ["not", "a", "mapping"],
                },
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
