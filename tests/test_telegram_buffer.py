"""Unit tests for Telegram photo buffering and command trigger logic."""

import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.telegram_buffer import TelegramBufferManager
from core import config


class TestTelegramBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer_mgr = TelegramBufferManager()
        self.buffer_mgr.BUFFER_FILE = config.STATE_DIR / "test_telegram_buffer.json"
        if self.buffer_mgr.BUFFER_FILE.exists():
            self.buffer_mgr.BUFFER_FILE.unlink()

    def tearDown(self):
        if self.buffer_mgr.BUFFER_FILE.exists():
            self.buffer_mgr.BUFFER_FILE.unlink()

    def test_buffer_initialization_and_clear(self):
        photos = self.buffer_mgr.get_buffered_photos()
        self.assertEqual(len(photos), 0)

        buf = self.buffer_mgr._load_buffer()
        buf["buffered_photos"].append({"slide_index": 1, "raw_path": "mock.jpg"})
        self.buffer_mgr._save_buffer(buf)

        self.assertEqual(len(self.buffer_mgr.get_buffered_photos()), 1)

        self.buffer_mgr.clear_buffer()
        self.assertEqual(len(self.buffer_mgr.get_buffered_photos()), 0)

    @patch("requests.get")
    @patch("core.telemetry.TelemetryClient.send_message")
    def test_process_incoming_photo(self, mock_send, mock_get):
        # Mock getUpdates returning 1 photo
        mock_updates_resp = MagicMock()
        mock_updates_resp.status_code = 200
        mock_updates_resp.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 101,
                    "message": {
                        "photo": [{"file_id": "photo_123"}]
                    }
                }
            ]
        }

        # Mock getFile and download
        mock_file_resp = MagicMock()
        mock_file_resp.json.return_value = {"ok": True, "result": {"file_path": "photos/p1.jpg"}}
        mock_file_resp.content = b"fake_image_bytes"

        mock_get.side_effect = [mock_updates_resp, mock_file_resp, mock_file_resp]

        should_trigger, photos, reason = self.buffer_mgr.process_incoming_updates(max_stories=9)

        self.assertFalse(should_trigger)
        self.assertEqual(len(photos), 1)
        self.assertEqual(photos[0]["file_id"], "photo_123")
        mock_send.assert_called_once()
        self.assertIn("Image 1/9 Received", mock_send.call_args[0][0])

    @patch("requests.get")
    def test_process_trigger_command(self, mock_get):
        mock_updates_resp = MagicMock()
        mock_updates_resp.status_code = 200
        mock_updates_resp.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 102,
                    "message": {
                        "text": "/process"
                    }
                }
            ]
        }
        mock_get.return_value = mock_updates_resp

        should_trigger, photos, reason = self.buffer_mgr.process_incoming_updates(max_stories=9)

        self.assertTrue(should_trigger)
        self.assertIn("/process", reason)


if __name__ == "__main__":
    unittest.main()
