"""Telegram bot telemetry, alerting, and interactive review."""

import html
import json
import re
from typing import Dict, Any, Optional
from core import config


class TelemetryClient:
    """Handles Telegram alerts, notifications, and operational logging."""

    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    def _sanitize(self, text: str) -> str:
        """Strips secret keys and tokens from messages before transmitting."""
        sanitized = text
        for secret in [
            config.POLLINATIONS_API_KEY,
            config.GEMINI_API_KEY,
            config.IG_ACCESS_TOKEN,
            config.TELEGRAM_BOT_TOKEN,
            config.CF_API_TOKEN,
            config.HF_TOKEN
        ]:
            if secret and len(secret) > 4:
                sanitized = sanitized.replace(secret, "[REDACTED]")
        # Mask any lingering sk_ or bearer patterns
        sanitized = re.sub(r"sk_[A-Za-z0-9_\-]{10,}", "[REDACTED_KEY]", sanitized)
        sanitized = re.sub(r"EA[A-Za-z0-9]{20,}", "[REDACTED_FB_TOKEN]", sanitized)
        return sanitized

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Transmits sanitized notification to configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            return False

        clean_text = self._sanitize(text)
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": clean_text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                print(f"[TELEMETRY WARNING] Telegram sendMessage failed ({resp.status_code}): {resp.text}")
            return resp.status_code == 200
        except Exception as e:
            print(f"[TELEMETRY ERROR] Exception sending Telegram message: {e}")
            return False

    def notify_success(
        self,
        mode: str,
        slot: str,
        slide_count: int,
        provider_breakdown: Dict[str, int],
        balance_left: Optional[float] = None,
        carousel_permalink: str = "",
        story_id: str = ""
    ) -> bool:
        """Sends rich success dispatch summary."""
        breakdown_str = " / ".join(f"{k}: {v}" for k, v in provider_breakdown.items())
        balance_str = f"{balance_left:.2f}" if balance_left is not None else "N/A"
        
        msg = (
            f"🎉 <b>INSTAGRAM POST PUBLISHED SUCCESSFULLY!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📸 <b>Slides:</b> {slide_count}\n"
            f"⚙️ <b>Mode:</b> Mode {mode.upper()} ({slot.upper()})\n"
        )
        if carousel_permalink:
            msg += (
                f"\n🔗 <b>Live Instagram Post Link:</b>\n"
                f"{carousel_permalink}\n\n"
                f"👉 <a href=\"{carousel_permalink}\">Click here to view your post on Instagram</a>"
            )
        if story_id:
            msg += f"\n📲 <b>Story ID:</b> <code>{story_id}</code>"

        return self.send_message(msg, parse_mode="HTML")

    def notify_warning(self, title: str, details: str) -> bool:
        """Sends operational warning (e.g. skipped feed, fallback triggered)."""
        msg = (
            f"<b>⚠️ Pipeline Warning: {title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{details}"
        )
        return self.send_message(msg, parse_mode="HTML")

    def send_admin_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Sends admin message to dedicated TELEGRAM_ADMIN_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID."""
        admin_token = getattr(config, "TELEGRAM_ADMIN_BOT_TOKEN", "") or self.bot_token
        admin_chat = getattr(config, "TELEGRAM_ADMIN_CHAT_ID", "") or self.chat_id

        if not admin_token or not admin_chat:
            return False

        clean_text = self._sanitize(text)
        try:
            import requests
            url = f"https://api.telegram.org/bot{admin_token}/sendMessage"
            payload = {
                "chat_id": admin_chat,
                "text": clean_text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def notify_error(self, stage: str, error_trace: str) -> bool:
        """Sends instant high-priority failure alert to Admin Chat ID with exact stage & sanitized traceback."""
        clean_trace = self._sanitize(error_trace)
        if len(clean_trace) > 3500:
            clean_trace = clean_trace[:3400] + "\n...[truncated]"

        msg = (
            f"<b>🚨 PIPELINE ERROR ALERT: Stage '{stage}' Failed!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>📍 Failed Stage:</b> {stage}\n"
            f"<b>⏰ Time:</b> {config.BASE_DIR.name}\n\n"
            f"<b>Error Traceback:</b>\n"
            f"<pre>{clean_trace}</pre>"
        )
        return self.send_admin_message(msg, parse_mode="HTML")

    def send_daily_api_report(
        self,
        duration_s: float,
        slides_count: int,
        meta_usage: dict = None,
        pollinations_balance: float = None,
        status: str = "SUCCESS"
    ) -> bool:
        """Sends daily API consumption, Meta Graph rate limits, and timing report to Admin Chat ID."""
        meta_info = "N/A"
        if meta_usage and isinstance(meta_usage, dict):
            # Extract Meta rate limit usage header stats if available
            meta_info = json.dumps(meta_usage, indent=2)

        p_balance = f"${pollinations_balance:.2f}" if pollinations_balance is not None else "N/A"

        msg = (
            f"<b>📊 DAILY API CONSUMPTION & HEALTH REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Status:</b> {'✅ SUCCESS' if status == 'SUCCESS' else '❌ FAILED'}\n"
            f"<b>⏱️ Pipeline Execution Time:</b> {duration_s:.1f} seconds\n"
            f"<b>📸 Slides Processed:</b> {slides_count}\n"
            f"<b>💰 Pollinations Balance:</b> {p_balance}\n"
            f"<b>📈 Meta Graph API Daily Usage:</b>\n"
            f"<pre>{meta_info}</pre>"
        )
        return self.send_admin_message(msg, parse_mode="HTML")

    def send_mode_n_reminder(self, permalink: str, slide_count: int = 9) -> bool:
        """Sends a reminder alert to Admin Bot (@Dailykeyupdatebot) when Mode N auto-news edition publishes."""
        msg = (
            f"📢 <b>AUTOMATED DAILY NEWS EDITION PUBLISHED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Notice: No custom Telegram photos were uploaded for today's post.</i>\n\n"
            f"📰 <b>Action Taken:</b> Automatically generated & published today's <b>{slide_count}-Slide Daily News Edition</b> from Google News RSS feeds!\n\n"
            f"🔗 <b>Live Post Link:</b>\n{permalink}\n\n"
            f"👉 <a href=\"{permalink}\">Click here to view live post on Instagram</a>"
        )
        return self.send_admin_message(msg, parse_mode="HTML")

    def send_headlight_prompts(self, prompts: list) -> int:
        """Dispatches the 9 @HEADLIGHTNEWS prompts to Telegram with 1-tap copyable blocks."""
        if not self.bot_token or not self.chat_id:
            return 0

        header_msg = (
            f"<b>📲 @HEADLIGHTNEWS PIPELINE — {len(prompts)} PROMPTS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Tap on any prompt block below to copy it with 1 tap, then paste into Midjourney, Flux, or Ideogram.\n\n"
            f"<i>Drop all {len(prompts)} generated images back into this chat when done!</i>"
        )
        self.send_message(header_msg, parse_mode="HTML")

        sent_count = 0
        for p in prompts:
            slide_idx = p.get("formatted_index", f"{p.get('slide_index', 1):02d}")
            raw_prompt = html.escape(p.get("raw_prompt", ""))
            msg = f"<b>SLIDE {slide_idx} / {len(prompts):02d} — PROMPT</b>\n<pre>{raw_prompt}</pre>"
            if self.send_message(msg, parse_mode="HTML"):
                sent_count += 1

        return sent_count

