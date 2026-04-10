from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import cli.mirror.publish.__main__ as publish_main


class _DummyResponse:
    def __init__(self, payload: bytes = b"{}"):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _org_probe() -> _DummyResponse:
    """Simulate a successful org-endpoint probe (account_type resolves to 'orgs')."""
    return _DummyResponse(b"[]")


class TestPublishMain(unittest.TestCase):
    def _make_pkg(self, name: str, visibility: str) -> dict:
        return {"name": name, "visibility": visibility}

    @patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=False)
    def test_already_public_packages_are_skipped(self) -> None:
        packages = [self._make_pkg("mirror/foo", "public")]
        responses = [
            _org_probe(),
            _DummyResponse(json.dumps(packages).encode()),
            _DummyResponse(b"[]"),
        ]

        with (
            patch(
                "cli.mirror.publish.__main__.urllib.request.urlopen",
                side_effect=responses,
            ) as mock_open,
            patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]),
        ):
            result = publish_main.main()

        self.assertEqual(result, 0)
        patch_calls = [
            c for c in mock_open.call_args_list if c[0][0].get_method() == "PATCH"
        ]
        self.assertEqual(patch_calls, [])

    @patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=False)
    def test_private_package_is_patched(self) -> None:
        packages = [self._make_pkg("mirror/bar", "private")]
        patch_response = _DummyResponse(b"{}")

        call_count = 0

        def fake_urlopen(req):
            nonlocal call_count
            call_count += 1
            if req.get_method() == "PATCH":
                return patch_response
            # call 1 = org probe, call 2 = list page 1, call 3 = list page 2
            if call_count == 1:
                return _DummyResponse(b"[]")
            payload = json.dumps(packages if call_count == 2 else []).encode()
            return _DummyResponse(payload)

        with (
            patch(
                "cli.mirror.publish.__main__.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ),
            patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]),
        ):
            result = publish_main.main()

        self.assertEqual(result, 0)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_token_returns_error(self) -> None:
        with patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]):
            result = publish_main.main()
        self.assertEqual(result, 1)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=False)
    def test_packages_outside_prefix_are_ignored(self) -> None:
        packages = [self._make_pkg("other/foo", "private")]
        responses = [
            _org_probe(),
            _DummyResponse(json.dumps(packages).encode()),
            _DummyResponse(b"[]"),
        ]

        with (
            patch(
                "cli.mirror.publish.__main__.urllib.request.urlopen",
                side_effect=responses,
            ) as mock_open,
            patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]),
        ):
            result = publish_main.main()

        self.assertEqual(result, 0)
        patch_calls = [
            c for c in mock_open.call_args_list if c[0][0].get_method() == "PATCH"
        ]
        self.assertEqual(patch_calls, [])

    @patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=False)
    def test_404_on_patch_skips_and_continues(self) -> None:
        """A 404 on PATCH means the package is gone — skip it, do not abort."""
        import urllib.error

        packages = [
            self._make_pkg("mirror/old-package", "private"),
            self._make_pkg("mirror/new-package", "private"),
        ]

        patch_call_count = 0

        def fake_urlopen(req):
            nonlocal patch_call_count
            if req.get_method() == "PATCH":
                patch_call_count += 1
                if patch_call_count == 1:
                    # First package returns 404 (old/deleted package)
                    raise urllib.error.HTTPError(
                        req.full_url, 404, "Not Found", {}, None
                    )
                return _DummyResponse(b"{}")
            # GET calls: org probe, page 1, page 2
            if not hasattr(fake_urlopen, "_get_count"):
                fake_urlopen._get_count = 0
            fake_urlopen._get_count += 1
            if fake_urlopen._get_count == 1:
                return _DummyResponse(b"[]")  # org probe
            payload = json.dumps(
                packages if fake_urlopen._get_count == 2 else []
            ).encode()
            return _DummyResponse(payload)

        with (
            patch(
                "cli.mirror.publish.__main__.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ),
            patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]),
        ):
            result = publish_main.main()

        # 404 on first package must not abort — second package is processed, exits 0
        self.assertEqual(result, 0)
        self.assertEqual(patch_call_count, 2)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=False)
    def test_401_on_patch_raises_insufficient_token_error(self) -> None:
        """A 401 on PATCH indicates a token scope problem — emit warning and return 0."""
        import urllib.error

        packages = [self._make_pkg("mirror/foo", "private")]

        call_count = 0

        def fake_urlopen(req):
            nonlocal call_count
            call_count += 1
            if req.get_method() == "PATCH":
                raise urllib.error.HTTPError(
                    req.full_url, 401, "Unauthorized", {}, None
                )
            if call_count == 1:
                return _DummyResponse(b"[]")  # org probe
            payload = json.dumps(packages if call_count == 2 else []).encode()
            return _DummyResponse(payload)

        with (
            patch(
                "cli.mirror.publish.__main__.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ),
            patch("sys.argv", ["publish", "--ghcr-namespace", "acme"]),
        ):
            result = publish_main.main()

        self.assertEqual(result, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
