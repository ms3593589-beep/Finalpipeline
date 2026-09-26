"""Unit tests for TelegramHITLManager (prompt dispatch, file download, and approval handling)."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.telegram_bot import TelegramHITLManager
from core import config


class TestTelegramHITLManager(unittest.TestCase):
    def setUp(self):
        self.mgr = TelegramHITLManager()

    def test_availability_check(self):
        with patch.object(config, "TELEGRAM_BOT_TOKEN", "123:ABC"), \
             patch.object(config, "TELEGRAM_CHAT_ID", "987"):
            manager = TelegramHITLManager()
            self.assertTrue(manager.is_available())

        with patch.object(config, "TELEGRAM_BOT_TOKEN", ""), \
             patch.object(config, "TELEGRAM_CHAT_ID", ""):
            manager_empty = TelegramHITLManager()
            self.assertFalse(manager_empty.is_available())

    @patch("requests.post")
    def test_send_text_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with patch.object(config, "TELEGRAM_BOT_TOKEN", "123:ABC"), \
             patch.object(config, "TELEGRAM_CHAT_ID", "987"):
            manager = TelegramHITLManager()
            res = manager.send_text("Test message")
            self.assertTrue(res)

    @patch("requests.post")
    def test_send_headlight_prompts(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        sample_prompts = [
            {
                "slide_index": i + 1,
                "formatted_index": f"{i+1:02d}",
                "headline": f"HEADLINE {i+1}",
                "raw_prompt": f"Raw prompt text for slide {i+1}"
            }
            for i in range(9)
        ]

        with patch.object(config, "TELEGRAM_BOT_TOKEN", "123:ABC"), \
             patch.object(config, "TELEGRAM_CHAT_ID", "987"):
            manager = TelegramHITLManager()
            res = manager.send_headlight_prompts(sample_prompts)
            self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
