"""Telegram Bot handler for prompt delivery, photo reception, and interactive publish approval."""

import os
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

from core import config


class TelegramHITLManager:
    """Manages Telegram interaction: sending prompts, receiving images, and awaiting publish approval."""

    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def is_available(self) -> bool:
        """Verifies Telegram credentials are configured."""
        return bool(self.bot_token and self.chat_id)

    def send_text(self, text: str, parse_mode: Optional[str] = "HTML", reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Sends text message to the target Telegram chat."""
        if not self.is_available():
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if reply_markup:
                payload["reply_markup"] = reply_markup

            resp = requests.post(url, json=payload, timeout=15)
            return resp.status_code == 200
        except Exception:
            return False

    def send_headlight_prompts(self, prompts: List[Dict[str, Any]]) -> bool:
        """
        Sends the 9 @HEADLIGHTNEWS prompts to Telegram as individual formatted messages
        with 1-tap copyable text blocks.
        """
        if not self.is_available():
            print("[TELEGRAM] Credentials missing. Prompts saved locally.")
            return False

        header_msg = (
            f"🗞️ <b>@HEADLIGHTNEWS — TODAY'S 9 INFOGRAPHIC PROMPTS</b>\n\n"
            f"Tap any prompt block below to copy it instantly. Generate the 9 images in Midjourney/Flux, "
            f"then send the 9 photos back to this chat!"
        )
        self.send_text(header_msg)

        success = True
        for p in prompts:
            slide_idx = p.get("formatted_index", f"{p.get('slide_index', 1):02d}")
            headline = p.get("headline", "")
            raw_block = p.get("raw_prompt", "")

            # Format block into Telegram HTML code block for 1-tap copy
            formatted_text = (
                f"📲 <b>SLIDE {slide_idx} / {len(prompts):02d} — {headline}</b>\n\n"
                f"<code>{raw_block}</code>"
            )
            if not self.send_text(formatted_text, parse_mode="HTML"):
                success = False
            time.sleep(0.5)

        footer_msg = (
            f"⏳ <b>AWAITING YOUR 9 GENERATED IMAGES</b>\n\n"
            f"Drop your 9 generated photos right here in this chat when ready!"
        )
        self.send_text(footer_msg)
        return success

    def download_file(self, file_id: str, destination_path: Path) -> bool:
        """Downloads a photo from Telegram servers to local filesystem."""
        if not self.is_available():
            return False
        try:
            get_file_url = f"{self.base_url}/getFile"
            resp = requests.post(get_file_url, json={"file_id": file_id}, timeout=15)
            if resp.status_code != 200:
                return False
            file_path = resp.json().get("result", {}).get("file_path")
            if not file_path:
                return False

            download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            img_resp = requests.get(download_url, timeout=30)
            if img_resp.status_code == 200:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                destination_path.write_bytes(img_resp.content)
                return True
        except Exception:
            pass
        return False

    def poll_for_user_images(
        self,
        target_dir: Path,
        expected_count: int = 9,
        timeout_seconds: int = 1800
    ) -> List[Path]:
        """
        Polls Telegram getUpdates for incoming photos uploaded by the user.
        Downloads them sequentially to target_dir as slide_1.jpg ... slide_N.jpg.
        """
        if not self.is_available():
            return []

        print(f"[TELEGRAM] Listening for {expected_count} photos in Telegram chat...")
        downloaded_paths = []
        last_update_id = 0
        start_time = time.time()

        # Flush old updates
        try:
            resp = requests.get(f"{self.base_url}/getUpdates", timeout=10)
            if resp.status_code == 200:
                updates = resp.json().get("result", [])
                if updates:
                    last_update_id = updates[-1]["update_id"] + 1
        except Exception:
            pass

        while len(downloaded_paths) < expected_count:
            if time.time() - start_time > timeout_seconds:
                self.send_text(f"⚠️ <b>Timeout:</b> Did not receive all {expected_count} photos in time.")
                break

            try:
                url = f"{self.base_url}/getUpdates"
                params = {"offset": last_update_id, "timeout": 10}
                resp = requests.get(url, params=params, timeout=15)

                if resp.status_code == 200:
                    updates = resp.json().get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"] + 1
                        msg = update.get("message", {})

                        # Check for photo attachment or photo document
                        photo_list = msg.get("photo")
                        doc = msg.get("document")

                        file_id = None
                        if photo_list:
                            # Highest resolution photo is last in list
                            file_id = photo_list[-1]["file_id"]
                        elif doc and doc.get("mime_type", "").startswith("image/"):
                            file_id = doc["file_id"]

                        if file_id:
                            slide_num = len(downloaded_paths) + 1
                            save_path = target_dir / f"slide_{slide_num}.jpg"

                            if self.download_file(file_id, save_path):
                                downloaded_paths.append(save_path)
                                self.send_text(
                                    f"📥 Received <b>Slide {slide_num:02d} / {expected_count:02d}</b> ("
                                    f"Saved: {save_path.name})"
                                )
                                print(f"[TELEGRAM] Downloaded Slide {slide_num} -> {save_path.name}")

            except Exception as e:
                time.sleep(3)

            time.sleep(2)

        return downloaded_paths

    def send_approval_prompt(self, total_slides: int = 9) -> bool:
        """Sends confirmation message with inline publish button to Telegram."""
        if not self.is_available():
            return False

        markup = {
            "inline_keyboard": [
                [
                    {"text": "🚀 Publish to Instagram Now", "callback_data": "publish_now"},
                    {"text": "❌ Cancel Job", "callback_data": "cancel_job"}
                ]
            ]
        }
        msg = (
            f"✅ <b>ALL {total_slides} SLIDES RECEIVED & VERIFIED!</b>\n\n"
            f"Tap <b>Publish to Instagram Now</b> below to normalize, build story, format caption, and publish live!"
        )
        return self.send_text(msg, reply_markup=markup)

    def await_user_approval(self, timeout_seconds: int = 600) -> bool:
        """Listens for user confirmation (/publish, 'publish', or callback button)."""
        if not self.is_available():
            return True  # Auto-approve in local dry-run mode

        start_time = time.time()
        last_update_id = 0

        while time.time() - start_time < timeout_seconds:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {"offset": last_update_id, "timeout": 10}
                resp = requests.get(url, params=params, timeout=15)

                if resp.status_code == 200:
                    updates = resp.json().get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"] + 1

                        # Handle button callback
                        callback = update.get("callback_query")
                        if callback:
                            data = callback.get("data")
                            if data == "publish_now":
                                self.send_text("🚀 <b>Publishing initiated...</b>")
                                return True
                            elif data == "cancel_job":
                                self.send_text("❌ <b>Job cancelled by user.</b>")
                                return False

                        # Handle text reply
                        msg = update.get("message", {})
                        text = (msg.get("text") or "").strip().lower()
                        if text in ["/publish", "publish", "yes", "go", "ok", "ready"]:
                            self.send_text("🚀 <b>Publishing initiated...</b>")
                            return True
                        elif text in ["/cancel", "cancel", "no", "stop"]:
                            self.send_text("❌ <b>Job cancelled by user.</b>")
                            return False

            except Exception:
                time.sleep(3)

            time.sleep(2)

        self.send_text("⚠️ <b>Approval timeout expired.</b> Aborting publish.")
        return False
