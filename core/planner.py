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

    def plan_festival_carousel(
        self,
        festival: Dict[str, Any],
        days_diff: int
    ) -> Dict[str, Any]:
        """Creates slide deck specification for an active Festival (Mode C)."""
        name = festival["name"]
        theme = festival.get("theme", "")
        style_lock = festival.get("style_lock", "Sacred festive Indian art")

        if days_diff > 0:
            status = f"T-{days_diff} DAYS TO {name.upper()}"
        elif days_diff == 0:
            status = f"CELEBRATING {name.upper()} TODAY"
        else:
            status = f"{name.upper()} CELEBRATIONS"

        slide_concepts = [
            (f"The Sacred Spirit of {name}", f"Awakening the timeless devotion, joy, and culture of {name} across India."),
            ("Cosmic Mythology & Significance", "Ancient scriptures and stories that weave the divine fabric of this auspicious time."),
            ("Sacred Traditions & Rituals", "From glowing lamps to fragrant floral garlands and community feasts."),
            ("Artisan Craft & Living Heritage", "Centuries of handcrafted heritage honoring this festive grace."),
            ("Festive Blessings & Harmony", "Wishing abundance, light, and prosperity to all hearts and homes.")
        ]

        slides = []
        total = len(slide_concepts)
        for idx, (title, body) in enumerate(slide_concepts):
            prompt = f"{style_lock}, {title.lower()}, divine atmosphere, rich festive lighting{self.ART_DIRECTIVE}"
            slides.append({
                "slide_index": idx + 1,
                "total_slides": total,
                "header": f"FESTIVALS OF INDIA | {status}",
                "category": "FESTIVAL",
                "title": title,
                "body": body,
                "sources": "Cultural Archives of India",
                "image_prompt": prompt
            })

        return {
            "mode": "festival",
            "festival_name": name,
            "slides": slides
        }

    def plan_evergreen_carousel(self, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates slide deck specification for a Weekday Evergreen Theme (Mode D)."""
        theme_name = theme_data["theme"]
        style_lock = theme_data.get("style_lock", "Classic Indian cultural art")
        concepts = theme_data.get("narrative_concepts", ["The Living Heritage of India"])

        slides = []
        total = min(len(concepts), 7)
        for idx in range(total):
            concept = concepts[idx]
            prompt = f"{style_lock}, {concept.lower()}, highly detailed, fine art lighting{self.ART_DIRECTIVE}"
            slides.append({
                "slide_index": idx + 1,
                "total_slides": total,
                "header": f"HERITAGE SERIES | {theme_name.upper()}",
                "category": "HERITAGE",
                "title": concept,
                "body": f"Exploring the profound cultural depth and timeless aesthetics of {concept.lower()}.",
                "sources": "Heritage Vault",
                "image_prompt": prompt
            })

        return {
            "mode": "evergreen",
            "theme_name": theme_name,
            "slides": slides
        }

    def plan_topic_carousel(self, topic: str) -> Dict[str, Any]:
        """Creates slide deck specification for a custom topic override (Mode B)."""
        slides = []
        slide_titles = [
            f"Discovering {topic}",
            "Historical Roots & Legacy",
            "Key Elements & Significance",
            "Contemporary Perspectives",
            "The Lasting Impact"
        ]
        total = len(slide_titles)
        for idx, title in enumerate(slide_titles):
            prompt = f"Fine Indian art aesthetic illustrating {topic}: {title}, dynamic composition, cinematic lighting{self.ART_DIRECTIVE}"
            slides.append({
                "slide_index": idx + 1,
                "total_slides": total,
                "header": f"SPECIAL FEATURE | {topic.upper()[:30]}",
                "category": "FEATURE",
                "title": title,
                "body": f"A dedicated visual exploration into {topic.lower()}.",
                "sources": "Curated Archive",
                "image_prompt": prompt
            })

        return {
            "mode": "custom_topic",
            "topic": topic,
            "slides": slides
        }
