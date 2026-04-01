import importlib.util
import os
import pathlib
import tempfile
import unittest
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


class TestGetRequestsVerify(unittest.TestCase):
    def test_uses_explicit_requests_ca_bundle_when_present(self):
        with tempfile.NamedTemporaryFile() as handle:
            with patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": handle.name}, clear=False):
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


if __name__ == "__main__":
    unittest.main()
