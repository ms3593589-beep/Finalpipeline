"""Telegram photo batching and command buffer manager."""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from core import config
from core.telemetry import TelemetryClient


class TelegramBufferManager:
    """Buffers incoming photos from Telegram until user sends /process trigger or batch completes."""

    BUFFER_FILE = config.STATE_DIR / "telegram_buffer.json"

    def __init__(self):
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.telemetry = TelemetryClient()
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    def _load_buffer(self) -> Dict[str, Any]:
        """Loads state/telegram_buffer.json or returns default template."""
        if self.BUFFER_FILE.exists():
            try:
                with open(self.BUFFER_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_update_id": 0, "buffered_photos": [], "is_active_batch": True}

    def _save_buffer(self, data: Dict[str, Any]):
        """Persists state/telegram_buffer.json."""
        with open(self.BUFFER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_buffered_photos(self) -> List[Dict[str, Any]]:
        """Returns current buffered photos."""
        buf = self._load_buffer()
        return buf.get("buffered_photos", [])

    def _clear_physical_folder(self):
        """Physically deletes temporary raw slide files from disk folder."""
        try:
            out_dir = config.MOCK_PREVIEW_DIR
            if out_dir.exists():
                for f in out_dir.glob("telegram_raw_slide_*.jpg"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def start_new_batch(self):
        """Clears all buffered photos, deletes physical folder files, and marks active batch state as True."""
        self._clear_physical_folder()
        buf = self._load_buffer()
        buf["buffered_photos"] = []
        buf["is_active_batch"] = True
        self._save_buffer(buf)

    def clear_buffer(self):
        """Clears all buffered photos, deletes physical folder files, and resets batch state."""
        self._clear_physical_folder()
        buf = self._load_buffer()
        buf["buffered_photos"] = []
        buf["is_active_batch"] = False
        self._save_buffer(buf)


    def process_incoming_updates(self, max_stories: int = 9) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Polls Telegram updates:
        - '/new': Starts fresh batch, clears buffer, sets is_active_batch = True.
        - photo: If active batch, downloads & appends photo, replies 'Image X/N received'.
                 If no active batch, replies warning asking user to send /new first.
        - '/end', '/done', '/process', 'done', 'end': Marks batch complete & triggers processing.
        """
        if not self.bot_token:
            return False, [], "No bot token configured"

        buf = self._load_buffer()
        last_update_id = buf.get("last_update_id", 0)
        buffered_photos = buf.get("buffered_photos", [])
        is_active_batch = buf.get("is_active_batch", True)

        # Fetch updates from Telegram
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": last_update_id + 1, "timeout": 2}
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return False, buffered_photos, f"Telegram API error {resp.status_code}"
            
            data = resp.json()
            results = data.get("result", [])
        except Exception as e:
            return False, buffered_photos, f"Request failed: {str(e)}"

        should_trigger = False
        trigger_reason = ""

        for update in results:
            up_id = update.get("update_id", 0)
            if up_id > last_update_id:
                last_update_id = up_id
                buf["last_update_id"] = last_update_id

            msg = update.get("message", {}) or update.get("channel_post", {})
            text = (msg.get("text") or "").strip().lower()
            photos = msg.get("photo", [])

            # 1. Handle Batch Start Command (/start or /new)
            if text in ["/start", "start", "/new", "new"]:
                self._clear_physical_folder()
                buffered_photos = []
                buf["buffered_photos"] = buffered_photos
                buf["is_active_batch"] = True
                is_active_batch = True
                ack_msg = (
                    "<b>🆕 Fresh Batch Started!</b>\n"
                    "Buffer state cleared. Send your images now!\n"
                    "Type <code>/end</code> or <code>/done</code> when finished."
                )
                self.telemetry.send_message(ack_msg)


            # 2. Handle Completion Trigger Command (/end, /done, /publish, /process)
            elif text in ["/end", "end", "/done", "done", "/publish", "publish", "/process", "process", "go", "/go"]:
                should_trigger = True
                buf["is_active_batch"] = False
                is_active_batch = False
                photo_count = len(buffered_photos)
                trigger_reason = f"User sent batch completion command: '{text}' ({photo_count} photos in buffer)"
                
                if photo_count > 0:
                    ack_msg = (
                        f"🚀 <b>Batch Finalized with {photo_count} Image(s)!</b>\n"
                        f"Proceeding to normalize canvas, assemble captions, and publish carousel."
                    )
                else:
                    ack_msg = (
                        f"📢 <b>Batch Completion Command Received ('{text}')!</b>\n"
                        f"Triggering execution for pipeline processing."
                    )
                self.telemetry.send_message(ack_msg)



            # 3. Handle Incoming Photo Update
            elif photos:
                if not is_active_batch:
                    # Ignore photos arriving before /new command
                    warn_msg = (
                        "<b>⚠️ No Active Batch!</b>\n"
                        "Please send <code>/start</code> first to start a fresh batch before sending photos."
                    )
                    self.telemetry.send_message(warn_msg)
                    continue

                photo_file_id = photos[-1]["file_id"]
                slide_num = len(buffered_photos) + 1

                # Resolve file URL with timeout error handling
                try:
                    getFile_url = f"https://api.telegram.org/bot{self.bot_token}/getFile?file_id={photo_file_id}"
                    file_resp = requests.get(getFile_url, timeout=15).json()

                    if file_resp.get("ok"):
                        file_path = file_resp["result"]["file_path"]
                        dl_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                        img_data = requests.get(dl_url, timeout=20).content

                        out_dir = config.MOCK_PREVIEW_DIR
                        out_dir.mkdir(parents=True, exist_ok=True)
                        raw_save_path = out_dir / f"telegram_raw_slide_{slide_num}.jpg"
                        
                        with open(raw_save_path, "wb") as f:
                            f.write(img_data)

                        photo_entry = {
                            "slide_index": slide_num,
                            "file_id": photo_file_id,
                            "raw_path": str(raw_save_path),
                            "timestamp": time.time()
                        }
                        buffered_photos.append(photo_entry)
                        buf["buffered_photos"] = buffered_photos

                        # Send Instant Feedback Acknowledgment
                        ack_msg = (
                            f"<b>✅ Image {slide_num}/{max_stories} Received!</b>\n"
                            f"Saved to buffer. Send more photos or type <code>/end</code> when done."
                        )
                        self.telemetry.send_message(ack_msg)
                except Exception as e:
                    print(f"Warning: Failed to download Telegram photo (file_id={photo_file_id}): {e}")
                    continue


                    # Auto-trigger if target max stories reached
                    if len(buffered_photos) >= max_stories:
                        should_trigger = True
                        buf["is_active_batch"] = False
                        is_active_batch = False
                        trigger_reason = f"Reached target count of {max_stories} images."

        self._save_buffer(buf)

        return should_trigger, buffered_photos, trigger_reason


