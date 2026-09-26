"""Content planner for news editions, festivals, evergreen themes, and custom topics."""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core import config
from core.news import NewsEngine


class ContentPlanner:
    """Coordinates text generation, slide scripting, and image prompt crafting."""

    ART_DIRECTIVE = ", no text, no letters, no logo, no watermark, centered composition, subject inside the middle 80%"

    def __init__(self):
        self.news_engine = NewsEngine()

    def _call_gemini_rest(self, prompt: str) -> Optional[str]:
        """Calls Google Gemini API via lightweight direct REST endpoint."""
        if not config.GEMINI_API_KEY:
            return None
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_TEXT_MODEL}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": config.GEMINI_API_KEY
            }
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.4,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, headers=headers, json=body, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
        except Exception:
            pass
        return None

    def _call_pollinations_chat(self, prompt: str) -> Optional[str]:
        """Calls Pollinations OpenAI-compatible chat completions API."""
        try:
            import requests
            url = f"{config.POLLINATIONS_BASE_URL}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            if config.POLLINATIONS_API_KEY:
                headers["Authorization"] = f"Bearer {config.POLLINATIONS_API_KEY}"
            body = {
                "model": config.POLLINATIONS_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a professional news editor and social media art director. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4
            }
            resp = requests.post(url, headers=headers, json=body, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def plan_with_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Attempts Gemini first, falls back to Pollinations chat, and parses JSON output."""
        raw = self._call_gemini_rest(prompt)
        if not raw:
            raw = self._call_pollinations_chat(prompt)
        if raw:
            try:
                # Strip markdown code blocks if present
                clean = re.sub(r"^```json\s*", "", raw.strip())
                clean = re.sub(r"\s*```$", "", clean)
                return json.loads(clean)
            except Exception:
                pass
        return None

    def plan_news_edition(
        self,
        clustered_stories: List[Dict[str, Any]],
        edition_name: str = "Morning Edition"
    ) -> Dict[str, Any]:
        """Creates complete slide deck specification for a News Edition (Mode N)."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d %b %Y").upper()
        header_text = f"TOP {len(clustered_stories)} INDIA NEWS | {date_str} | {edition_name.upper()}"

        slides = []
        total = len(clustered_stories)

        for idx, story in enumerate(clustered_stories):
            rep_title = story["representative_title"]
            desc = story.get("description", "")
            category = story.get("category", "Top")
            sources_str = ", ".join(sorted(story.get("sources", ["News Wire"])))
            is_sensitive = story.get("is_sensitive", False)

            # Generate or heuristically build 1-sentence summary
            summary = desc if desc and len(desc) < 160 else rep_title
            # Validate number guard
            if not self.news_engine.validate_number_guard(summary, f"{rep_title} {desc}"):
                summary = rep_title

            # Construct symbolic image prompt
            if is_sensitive:
                base_prompt = "Solemn symbolic composition, warm candle flame illuminating ancient carved stone steps, peaceful stillness, dramatic quiet lighting, oil painting style"
            else:
                base_prompt = f"Editorial conceptual illustration of {category.lower()} in India: {rep_title}. Vibrant symbolic aesthetic, contemporary digital art style"

            image_prompt = base_prompt + self.ART_DIRECTIVE

            slides.append({
                "slide_index": idx + 1,
                "total_slides": total,
                "header": header_text,
                "category": category.upper(),
                "title": rep_title,
                "body": summary,
                "sources": f"Sources: {sources_str}",
                "image_prompt": image_prompt,
                "is_sensitive": is_sensitive
            })

        return {
            "mode": "news",
            "edition": edition_name,
            "header": header_text,
            "slides": slides,
            "stories": clustered_stories
        }
