"""Unit tests for Meta Graph API polling and Cloudinary staging cleanup."""

import unittest
from unittest.mock import patch, MagicMock
from publisher.meta_client import MetaPublisher
from publisher.cloudinary_client import CloudinaryStager
from core import config


class TestPublisherClients(unittest.TestCase):
    def setUp(self):
        config.IG_USER_ID = "17841400000000000"
        config.IG_ACCESS_TOKEN = "EAABtest_token_123"
        self.meta = MetaPublisher()
        self.stager = CloudinaryStager()

    @patch("requests.get")
    def test_meta_polling_finished(self, mock_get):
        # Container polling returns FINISHED
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_resp

        result = self.meta._poll_container_status("container_123", max_attempts=3, interval_s=0.01)
        self.assertTrue(result)

    @patch("requests.get")
    def test_meta_polling_error_aborts(self, mock_get):
        # Container polling returns ERROR -> must raise RuntimeError
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status_code": "ERROR"}
        mock_get.return_value = mock_resp

        with self.assertRaises(RuntimeError):
            self.meta._poll_container_status("container_123", max_attempts=3, interval_s=0.01)

    @patch("requests.get")
    def test_meta_polling_expired_aborts(self, mock_get):
        # Container polling returns EXPIRED -> must raise RuntimeError
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status_code": "EXPIRED"}
        mock_get.return_value = mock_resp

        with self.assertRaises(RuntimeError):
            self.meta._poll_container_status("container_123", max_attempts=3, interval_s=0.01)

    @patch("requests.get")
    def test_meta_polling_timeout(self, mock_get):
        # Container remains IN_PROGRESS -> must raise TimeoutError
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status_code": "IN_PROGRESS"}
        mock_get.return_value = mock_resp

        with self.assertRaises(TimeoutError):
            self.meta._poll_container_status("container_123", max_attempts=2, interval_s=0.01)

    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.api.delete_resources_by_prefix")
    def test_cloudinary_destroy_called_on_cleanup(self, mock_prefix_del, mock_destroy):
        self.stager.configured = True
        self.stager.uploaded_public_ids = ["igpipe/job_1/slide_1", "igpipe/job_1/slide_2"]

        self.stager.cleanup_all("job_1")

        # Verify destroy was invoked for each staged asset
        self.assertEqual(mock_destroy.call_count, 2)
        mock_prefix_del.assert_called_with("igpipe/job_1/")
        self.assertEqual(len(self.stager.uploaded_public_ids), 0)


if __name__ == "__main__":
    unittest.main()
