import importlib.util
import os
import pathlib
import tempfile
import unittest
from ansible.errors import AnsibleFilterError
from unittest.mock import patch

import certifi


def _load_simpleicons_module():
    test_file = pathlib.Path(__file__).resolve()
    repo_root = test_file.parents[5]

    module_path = (
        repo_root
        / "roles"
        / "web-app-dashboard"
        / "filter_plugins"
        / "simpleicons_source.py"
    )

    if not module_path.is_file():
        raise RuntimeError(
            f"Could not find simpleicons_source.py at expected path: {module_path}"
        )

    spec = importlib.util.spec_from_file_location("simpleicons_source", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_simpleicons = _load_simpleicons_module()
get_requests_verify = _simpleicons.get_requests_verify
add_simpleicon_source = _simpleicons.add_simpleicon_source


class TestGetRequestsVerify(unittest.TestCase):
    def test_uses_explicit_requests_ca_bundle_when_present(self):
        with tempfile.NamedTemporaryFile() as handle:
            with patch.dict(
                os.environ, {"REQUESTS_CA_BUNDLE": handle.name}, clear=False
            ):
                self.assertEqual(get_requests_verify(), handle.name)

    def test_falls_back_to_certifi_bundle_when_no_env_ca_exists(self):
        with patch.dict(
            os.environ,
            {
                "REQUESTS_CA_BUNDLE": "",
                "SSL_CERT_FILE": "",
                "CA_TRUST_CERT_HOST": "",
            },
            clear=False,
        ):
            self.assertEqual(get_requests_verify(), certifi.where())

    def test_ignores_missing_env_bundle_and_keeps_verification_enabled(self):
        with patch.dict(
            os.environ,
            {"REQUESTS_CA_BUNDLE": "/definitely/missing/ca.pem"},
            clear=False,
        ):
            self.assertEqual(get_requests_verify(), certifi.where())


class TestAddSimpleiconSource(unittest.TestCase):
    def test_uses_dashboard_local_static_svg_path_when_icon_exists(self):
        cards = [{"title": "Keycloak", "icon": {"class": "fa-solid fa-lock"}}]

        with (
            patch.object(
                _simpleicons, "get_requests_verify", return_value="/tmp/test-ca.crt"
            ),
            patch.object(_simpleicons.requests, "head") as mock_head,
        ):
            mock_head.return_value.status_code = 200

            result = add_simpleicon_source(cards, "https://icons.example")

        self.assertEqual(result[0]["icon"]["source"], "simpleicons/keycloak.svg")
        self.assertEqual(result[0]["icon"]["class"], "fa-solid fa-lock")
        mock_head.assert_called_once_with(
            "https://icons.example/keycloak.svg",
            timeout=2,
            allow_redirects=True,
            verify="/tmp/test-ca.crt",
        )

    def test_keeps_card_without_source_when_icon_does_not_exist(self):
        cards = [{"title": "Missing", "icon": {"class": "fa-solid fa-circle-question"}}]

        with patch.object(_simpleicons.requests, "head") as mock_head:
            mock_head.return_value.status_code = 404

            result = add_simpleicon_source(cards, "https://icons.example")

        self.assertNotIn("source", result[0]["icon"])
        mock_head.assert_called_once()

    def test_rejects_empty_dashboard_local_static_directory(self):
        with self.assertRaises(AnsibleFilterError):
            add_simpleicon_source(
                [{"title": "Keycloak", "icon": {}}],
                "https://icons.example",
                local_static_dir="/",
            )


if __name__ == "__main__":
    unittest.main()
