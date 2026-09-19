"""Unit tests for PollinationsProvider HTTP responses, status codes, and error transitions."""

import io
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

from images.pollinations import PollinationsProvider
from core import config


class TestPollinationsProvider(unittest.TestCase):
    def setUp(self):
        # Configure a test key
        config.POLLINATIONS_API_KEY = "sk_test_key_12345"
        config.POLLINATIONS_MIN_INTERVAL_S = 0.0
        self.provider = PollinationsProvider()
        self.provider.active_model = "flux"

    def _create_mock_image_bytes(self) -> bytes:
        img = Image.new("RGB", (1024, 1280), color=(50, 100, 150))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    @patch("requests.get")
    def test_pollinations_success_200(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.content = self._create_mock_image_bytes()
        mock_get.return_value = mock_resp

        img = self.provider.generate("Test prompt", seed=123)
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (1024, 1280))
        self.assertFalse(self.provider.is_exhausted)

    @patch("requests.get")
    def test_pollinations_401_marks_exhausted(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        img = self.provider.generate("Test prompt", seed=123)
        self.assertIsNone(img)
        self.assertTrue(self.provider.is_exhausted)
        self.assertFalse(self.provider.is_available())

    @patch("requests.get")
    def test_pollinations_402_marks_exhausted(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_get.return_value = mock_resp

        img = self.provider.generate("Test prompt", seed=123)
        self.assertIsNone(img)
        self.assertTrue(self.provider.is_exhausted)

    @patch("images.pollinations.time.sleep")
    @patch("requests.get")
    def test_pollinations_429_retry_after_success(self, mock_get, mock_sleep):
        # First attempt: 429 with Retry-After 1.0; Second attempt: 200 OK
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "1.0"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.headers = {"Content-Type": "image/jpeg"}
        resp_200.content = self._create_mock_image_bytes()

        mock_get.side_effect = [resp_429, resp_200]

        img = self.provider.generate("Test prompt", seed=123)
        self.assertIsNotNone(img)
        mock_sleep.assert_called_with(1.0)

    @patch("images.pollinations.time.sleep")
    @patch("requests.get")
    def test_pollinations_502_retry_then_fallthrough(self, mock_get, mock_sleep):
        resp_502 = MagicMock()
        resp_502.status_code = 502
        mock_get.return_value = resp_502

        img = self.provider.generate("Test prompt", seed=123)
        self.assertIsNone(img)
        # Should have attempted retries
        self.assertGreaterEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
