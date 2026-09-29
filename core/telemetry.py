"""Telegram bot telemetry, alerting, and interactive review."""

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
            return resp.status_code == 200
        except Exception:
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
            f"<b>✅ Instagram Pipeline Published</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Slot / Mode:</b> {slot.upper()} (Mode {mode.upper()})\n"
            f"<b>Slides:</b> {slide_count} ({breakdown_str})\n"
            f"<b>Pollen Balance:</b> {balance_str}\n"
        )
        if carousel_permalink:
            msg += f"<b>Post Link:</b> <a href=\"{carousel_permalink}\">View on Instagram</a>\n"
        if story_id:
            msg += f"<b>Story ID:</b> <code>{story_id}</code>\n"

        return self.send_message(msg, parse_mode="HTML")

    def notify_warning(self, title: str, details: str) -> bool:
        """Sends operational warning (e.g. skipped feed, fallback triggered)."""
        msg = (
            f"<b>⚠️ Pipeline Warning: {title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{details}"
        )
        return self.send_message(msg, parse_mode="HTML")

    def notify_error(self, stage: str, error_trace: str) -> bool:
        """Sends failure alert with sanitized traceback truncated to 3,500 chars."""
        clean_trace = self._sanitize(error_trace)
        if len(clean_trace) > 3500:
            clean_trace = clean_trace[:3400] + "\n...[truncated]"

        msg = (
            f"<b>🚨 Pipeline Error in Stage: {stage}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{clean_trace}</pre>"
        )
        return self.send_message(msg, parse_mode="HTML")

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
            raw_prompt = p.get("raw_prompt", "")
            msg = f"<b>SLIDE {slide_idx} / {len(prompts):02d} — PROMPT</b>\n<pre>{raw_prompt}</pre>"
            if self.send_message(msg, parse_mode="HTML"):
                sent_count += 1

        return sent_count

