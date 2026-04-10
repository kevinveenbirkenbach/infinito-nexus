from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from tests.external.repository import test_urls_reachable as sut


class TestProbeUrl(unittest.TestCase):
    def _response(self, status_code: int) -> Mock:
        response = Mock()
        response.status_code = status_code
        response.close = Mock()
        return response

    @patch.object(sut.requests, "get")
    def test_probe_returns_fail_for_client_error(self, mock_get: Mock) -> None:
        mock_get.return_value = self._response(404)

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "fail")
        self.assertEqual(outcome.detail, "HTTP 404")

    @patch.object(sut.requests, "get")
    def test_probe_returns_warn_for_http_503(self, mock_get: Mock) -> None:
        mock_get.return_value = self._response(503)

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "warn")
        self.assertEqual(outcome.detail, "HTTP 503")

    @patch.object(sut.requests, "get")
    def test_probe_returns_fail_for_non_warn_server_error(self, mock_get: Mock) -> None:
        mock_get.return_value = self._response(502)

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "fail")
        self.assertEqual(outcome.detail, "HTTP 502")

    @patch.object(sut.requests, "get")
    def test_probe_returns_warn_for_http_500(self, mock_get: Mock) -> None:
        mock_get.return_value = self._response(500)

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "warn")
        self.assertEqual(outcome.detail, "HTTP 500")

    @patch.object(sut.requests, "get")
    def test_probe_returns_ok_for_auth_gated(self, mock_get: Mock) -> None:
        mock_get.return_value = self._response(401)

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "ok")

    @patch.object(sut.requests, "get")
    def test_probe_returns_fail_for_unreachable_url(self, mock_get: Mock) -> None:
        mock_get.side_effect = sut.requests.ConnectionError("dns failed")

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "fail")
        self.assertIn("ConnectionError", outcome.detail)

    @patch.object(sut.requests, "get")
    def test_probe_returns_warn_for_timeout(self, mock_get: Mock) -> None:
        mock_get.side_effect = sut.requests.Timeout("timed out")

        outcome = sut._probe_url("https://example.invalid/path")

        self.assertEqual(outcome.kind, "warn")
        self.assertIn("Timeout", outcome.detail)


class TestUrlReachabilityTestCase(unittest.TestCase):
    def test_external_check_fails_and_emits_error_annotation(self) -> None:
        case = sut.TestUrlsReachable()
        occurrence = sut.UrlOccurrence(
            sut._REPO_ROOT / "docs/file.md", 7, "https://bad.example"
        )

        with (
            patch.object(
                sut,
                "_collect_occurrences",
                return_value={"https://bad.example": [occurrence]},
            ),
            patch.object(
                sut,
                "_probe_url",
                return_value=sut.ProbeOutcome("fail", "HTTP 404"),
            ),
            patch.object(sut, "error") as mock_error,
            patch.object(sut, "warning") as mock_warning,
        ):
            with self.assertRaises(AssertionError) as cm:
                case.test_public_http_urls_are_reachable()

        self.assertIn("HTTP 404", str(cm.exception))
        mock_error.assert_called_once()
        mock_warning.assert_not_called()

    def test_external_check_warns_for_http_500_without_failing(self) -> None:
        case = sut.TestUrlsReachable()
        occurrence = sut.UrlOccurrence(
            sut._REPO_ROOT / "docs/file.md", 7, "https://warn.example"
        )

        with (
            patch.object(
                sut,
                "_collect_occurrences",
                return_value={"https://warn.example": [occurrence]},
            ),
            patch.object(
                sut,
                "_probe_url",
                return_value=sut.ProbeOutcome("warn", "HTTP 500"),
            ),
            patch.object(sut, "error") as mock_error,
            patch.object(sut, "warning") as mock_warning,
        ):
            case.test_public_http_urls_are_reachable()

        mock_error.assert_not_called()
        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
