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
                    "temperature": config.GEMINI_PROMPT_TEMPERATURE,
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
                "temperature": config.GEMINI_PROMPT_TEMPERATURE
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
                clean = re.sub(r"^```json\s*", "", raw.strip(), flags=re.IGNORECASE)
                clean = re.sub(r"\s*```$", "", clean)
                return json.loads(clean)
            except Exception:
                pass
        return None

    def _build_gemini_news_prompt(self, candidates: List[Dict[str, Any]], target_count: int = 9) -> str:
        """Constructs prompt for Gemini to select Top 9 stories and generate visual prompts."""
        prompt_data = []
        for idx, c in enumerate(candidates):
            prompt_data.append({
                "candidate_id": idx,
                "title": c.get("representative_title", ""),
                "description": c.get("description", ""),
                "category": c.get("category", "Top"),
                "is_sensitive": c.get("is_sensitive", False)
            })

        return (
            f"You are a senior news editor and social media art director for India's premier daily visual news carousel.\n"
            f"From the following candidate news stories from India today, select exactly {target_count} most important, "
            f"diverse, and high-impact breaking stories across India (covering national affairs, economy, technology, sports, and major events).\n\n"
            f"For each selected story, generate a JSON object with:\n"
            f"- candidate_id: integer corresponding to the candidate_id from the input list\n"
            f"- headline: punchy, factual headline (maximum 70 characters)\n"
            f"- summary: crisp, informative single-sentence explanation (maximum 140 characters). "
            f"CRITICAL: Do NOT invent or hallucinate any numbers, statistics, or metrics not explicitly present in the original title or description.\n"
            f"- category: single uppercase category word (e.g., TECH, NATION, ECONOMY, SPORTS, DEFENCE, INFRA, GLOBAL)\n"
            f"- art_prompt: a symbolic, atmospheric visual editorial scene capturing the essence and core metaphor of the news story. "
            f"Focus on photographic realism or cinematic editorial illustration. Do NOT include any text, letters, signage, or logos in the scene description.\n\n"
            f"Return ONLY valid JSON matching this schema:\n"
            f'{{"stories": [{{"candidate_id": 0, "headline": "...", "summary": "...", "category": "...", "art_prompt": "..."}}]}}\n\n'
            f"Candidates:\n{json.dumps(prompt_data, ensure_ascii=False)}"
        )

    def _plan_with_gemini(
        self,
        clustered_stories: List[Dict[str, Any]],
        target_count: int = 9
    ) -> Optional[List[Dict[str, Any]]]:
        """Queries Gemini to select top stories and script visual prompts with Number Guard."""
        prompt = self._build_gemini_news_prompt(clustered_stories, target_count=target_count)
        result = self.plan_with_llm(prompt)
        if not result or not isinstance(result, dict):
            return None

        stories_data = result.get("stories")
        if not isinstance(stories_data, list) or len(stories_data) < min(2, target_count):
            return None

        parsed_stories = []
        for item in stories_data[:target_count]:
            cid = item.get("candidate_id")
            if isinstance(cid, int) and 0 <= cid < len(clustered_stories):
                orig = clustered_stories[cid]
            else:
                orig = clustered_stories[len(parsed_stories) % len(clustered_stories)]

            headline = (item.get("headline") or orig["representative_title"]).strip()[:75]
            summary = (item.get("summary") or orig.get("description", "")).strip()[:160]
            category = (item.get("category") or orig.get("category", "TOP")).strip().upper()
            art_prompt = (item.get("art_prompt") or "").strip()
            is_sensitive = orig.get("is_sensitive", False)

            # Validate Number Guard against source
            orig_text = f"{orig['representative_title']} {orig.get('description', '')}"
            if not self.news_engine.validate_number_guard(summary, orig_text):
                summary = orig.get("description") or orig["representative_title"]
                if len(summary) > 160:
                    summary = orig["representative_title"]

            # Fallback art prompt if missing or empty
            if not art_prompt:
                if is_sensitive:
                    art_prompt = "Solemn symbolic composition, warm candle flame illuminating ancient carved stone steps, peaceful stillness, dramatic quiet lighting, oil painting style"
                else:
                    art_prompt = f"Editorial conceptual illustration of {category.lower()} in India: {headline}. Vibrant symbolic aesthetic, contemporary digital art style"

            image_prompt = art_prompt + self.ART_DIRECTIVE
            sources_str = ", ".join(sorted(orig.get("sources", ["News Wire"])))

            parsed_stories.append({
                "title": headline,
                "body": summary,
                "category": category,
                "sources": f"Sources: {sources_str}",
                "image_prompt": image_prompt,
                "is_sensitive": is_sensitive
            })

        return parsed_stories if len(parsed_stories) >= 2 else None

    def _plan_heuristically(
        self,
        clustered_stories: List[Dict[str, Any]],
        target_count: int = 9
    ) -> List[Dict[str, Any]]:
        """Deterministic local heuristic fallback when Gemini API is unavailable or offline."""
        stories = clustered_stories[:target_count]
        parsed_stories = []

        for story in stories:
            rep_title = story["representative_title"]
            desc = story.get("description", "")
            category = story.get("category", "Top").upper()
            sources_str = ", ".join(sorted(story.get("sources", ["News Wire"])))
            is_sensitive = story.get("is_sensitive", False)

            summary = desc if desc and len(desc) < 160 else rep_title
            if not self.news_engine.validate_number_guard(summary, f"{rep_title} {desc}"):
                summary = rep_title

            if is_sensitive:
                base_prompt = "Solemn symbolic composition, warm candle flame illuminating ancient carved stone steps, peaceful stillness, dramatic quiet lighting, oil painting style"
            else:
                base_prompt = f"Editorial conceptual illustration of {category.lower()} in India: {rep_title}. Vibrant symbolic aesthetic, contemporary digital art style"

            image_prompt = base_prompt + self.ART_DIRECTIVE

            parsed_stories.append({
                "title": rep_title,
                "body": summary,
                "category": category,
                "sources": f"Sources: {sources_str}",
                "image_prompt": image_prompt,
                "is_sensitive": is_sensitive
            })

        return parsed_stories

    def plan_news_edition(
        self,
        clustered_stories: List[Dict[str, Any]],
        edition_name: str = "Morning Edition"
    ) -> Dict[str, Any]:
        """Creates complete slide deck specification for a News Edition (Mode N)."""
        target_count = min(len(clustered_stories), config.NEWS_MAX_STORIES)
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d %b %Y").upper()

        # Attempt Gemini AI planning first
        planned_items = None
        if config.GEMINI_API_KEY:
            try:
                planned_items = self._plan_with_gemini(clustered_stories, target_count=target_count)
            except Exception:
                planned_items = None

        # Fallback to deterministic heuristic planning if Gemini was unavailable
        if not planned_items:
            planned_items = self._plan_heuristically(clustered_stories, target_count=target_count)

        total_slides = len(planned_items)
        header_text = f"TOP {total_slides} INDIA NEWS | {date_str} | {edition_name.upper()}"

        slides = []
        for idx, item in enumerate(planned_items):
            slides.append({
                "slide_index": idx + 1,
                "total_slides": total_slides,
                "header": header_text,
                "category": item["category"],
                "title": item["title"],
                "body": item["body"],
                "sources": item["sources"],
                "image_prompt": item["image_prompt"],
                "is_sensitive": item["is_sensitive"]
            })

        return {
            "mode": "news",
            "edition": edition_name,
            "header": header_text,
            "slides": slides,
            "stories": clustered_stories[:total_slides]
        }

