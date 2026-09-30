"""Content planner for news editions, festivals, evergreen themes, and custom topics."""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core import config
from core.news import NewsEngine


class ContentPlanner:
    """Coordinates text generation, slide scripting, and image prompt crafting."""

    INFOGRAPHIC_MASTER_PROMPT_TEMPLATE = (
        "A professional breaking news vertical infographic, 9:16 portrait, clean editorial design.\n\n"
        "TOP LEFT: neat black uppercase text: \"{date_text}\".\n"
        "TOP RIGHT: a black triple chevron icon (>>>).\n\n"
        "HEADLINE: large, bold, black, condensed uppercase sans-serif, left-aligned, max 3 lines, reading exactly: \"{headline}\".\n\n"
        "LABEL: directly below the headline, a solid bright red rectangular box with white bold uppercase text: \"{category}\".\n\n"
        "BODY TEXT: below the red box, two lines at most of black, medium-weight sans-serif text (about 60% of the headline size, generous line spacing), reading exactly: \"{summary}\". No other body text, no source names, no extra words.\n\n"
        "PHOTO: below the text, a smooth white-to-fog gradient fade into a full-width photograph. The photograph is: {art_prompt}. Dramatic photojournalistic style, 35mm lens, shallow depth of field, low atmospheric lighting, editorial documentary framing. No readable text, letters, logos or flags in the photo. Keep the photo dark at the bottom so white footer text stays readable.\n\n"
        "FOOTER: bottom right only, white bold uppercase text: \"@DEEPBROTHERSNEWS\". Nothing else in the footer: no badge, no number, no other shapes.\n\n"
        "Typography is crisp and correctly spelled, with consistent margins and strong hierarchy: headline, label, body, photo, footer."
    )

    def format_infographic_prompt(
        self,
        headline: str,
        category: str,
        summary: str,
        art_prompt: str,
        date_text: Optional[str] = None
    ) -> str:
        """Formats the master infographic prompt specification with story metadata."""
        if not date_text:
            date_text = datetime.now(timezone.utc).strftime("%d %b %Y").upper()
        return self.INFOGRAPHIC_MASTER_PROMPT_TEMPLATE.format(
            date_text=date_text,
            headline=headline,
            category=category.upper(),
            summary=summary,
            art_prompt=art_prompt
        )

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

            image_prompt = self.format_infographic_prompt(
                headline=headline,
                category=category,
                summary=summary,
                art_prompt=art_prompt
            )
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

            image_prompt = self.format_infographic_prompt(
                headline=rep_title,
                category=category,
                summary=summary,
                art_prompt=base_prompt
            )

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

    def _call_gemini_text(self, prompt: str, temperature: float = 0.35) -> Optional[str]:
        """Calls Google Gemini API for free-form formatted text generation."""
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
                    "temperature": temperature
                }
            }
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
        except Exception:
            pass
        return None

    def build_headlight_prompt(self, candidates: List[Dict[str, Any]], target_count: int = 9) -> str:
        """Constructs prompt using the exact user-specified @HEADLIGHTNEWS template."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%A, %d %B %Y")

        news_items = []
        for idx, c in enumerate(candidates):
            news_items.append({
                "id": idx,
                "title": c.get("representative_title", ""),
                "description": c.get("description", ""),
                "category": c.get("category", "Top"),
                "is_sensitive": c.get("is_sensitive", False)
            })

        return (
            f'You are an expert news editor and AI prompt engineer for "@HEADLIGHTNEWS".\n\n'
            f'TODAY\'S DATE: {date_str}\n\n'
            f'TASK:\n'
            f'1. Review today\'s candidate news stories below and identify the top {target_count} national and global news stories across diverse categories (Nation, Economy, Tech, World, Sports).\n'
            f'2. For each of the {target_count} stories (numbered 01 to {target_count:02d}), convert it into our exact standardized vertical infographic prompt for text-to-image generators (Midjourney, Flux, Ideogram).\n\n'
            f'STRICT TEMPLATE FORMAT FOR EVERY STORY (Do not alter the skeleton):\n\n'
            f'Headline Section:\n'
            f'A professional breaking news vertical infographic. At the top left, neat black uppercase text displaying today\'s date: "{date_str.upper()}". At the top right, a black triple chevron icon (>>>).\n\n'
            f'Dynamic Text:\n'
            f'Large, bold black uppercase typography reading: "[INSERT GENERATED BIG HEADLINE]".\n'
            f'Directly below the headline, a solid bright red horizontal rectangular box containing white bold uppercase text: "[INSERT GENERATED RED BADGE KEYWORD]".\n'
            f'Below the red box, smaller black body text with exact spelling: "[INSERT GENERATED STORY DETAILS SUMMARY]".\n\n'
            f'Dynamic Image:\n'
            f'In the center, a soft, smooth white-to-fog fade transitions into the main photograph below. The photograph is a [INSERT GENERATED 3-PART PHOTO SCENE].\n\n'
            f'Footer Section:\n'
            f'At the bottom left, a clean red square badge with white number "[TWO DIGIT INDEX: 01 to {target_count:02d}]". At the bottom right, white bold text handle: "@HEADLIGHTNEWS".\n\n'
            f'RULES FOR INSERTS:\n'
            f'- [BIG HEADLINE]: Bold, strictly UPPERCASE, punchy (maximum 10–12 words).\n'
            f'- [RED BADGE KEYWORD]: 1–3 words in UPPERCASE (e.g., POLICY SHIFT, BREAKING UPDATE, DIPLOMACY, MEDAL HAUL).\n'
            f'- [STORY DETAILS SUMMARY]: Exactly 1 concise, factual sentence. CRITICAL: Do NOT invent or hallucinate any numbers or metrics not present in the source.\n'
            f'- [3-PART PHOTO SCENE]:\n'
            f'  * Part 1 (Subject & Action): Tangible real-world human subjects, vehicles, or physical objects performing an action. (Avoid metaphors, floating icons, or abstract concepts).\n'
            f'  * Part 2 (Setting & Background): Concrete, realistic environment (e.g., podium in a summit hall, flood-hit paved street, high-tech server racks).\n'
            f'  * Part 3 (Visual Tone Anchor): Always append verbatim: "dramatic photojournalistic style, low atmospheric lighting, editorial documentary framing, 35mm depth of field".\n\n'
            f'Emit all {target_count} prompts sequentially, separated by a horizontal line (---).\n\n'
            f'TODAY\'S CANDIDATE STORIES FROM GOOGLE NEWS:\n'
            f'{json.dumps(news_items, ensure_ascii=False)}'
        )

    def parse_headlight_blocks(self, raw_text: str, candidates: List[Dict[str, Any]], target_count: int = 9) -> List[Dict[str, Any]]:
        """Parses the @HEADLIGHTNEWS sequential prompt output separated by '---'."""
        blocks = [b.strip() for b in raw_text.split("---") if b.strip()]
        results = []

        for idx, block in enumerate(blocks[:target_count]):
            slide_idx = idx + 1
            if "Footer Section:" not in block:
                block = block.rstrip() + f'\n\nFooter Section:\nAt the bottom left, a clean red square badge with white number "{slide_idx:02d}". At the bottom right, white bold text handle: "@HEADLIGHTNEWS".'

            headline_match = re.search(r'reading:\s*"([^"]+)"', block, re.IGNORECASE)
            headline = headline_match.group(1).strip() if headline_match else f"BREAKING NEWS STORY {slide_idx}"

            badge_match = re.search(r'containing white bold uppercase text:\s*"([^"]+)"', block, re.IGNORECASE)
            badge = badge_match.group(1).strip() if badge_match else "TOP UPDATE"

            summary_match = re.search(r'smaller black body text with exact spelling:\s*"([^"]+)"', block, re.IGNORECASE)
            summary = summary_match.group(1).strip() if summary_match else headline

            photo_match = re.search(r'The photograph is a\s+(.*?)(?:\.\s*Footer Section|\nFooter Section|Footer Section)', block, re.DOTALL | re.IGNORECASE)
            photo_scene = photo_match.group(1).strip() if photo_match else ""

            matched_candidate = candidates[idx % len(candidates)] if candidates else {}
            cand_text = f"{matched_candidate.get('representative_title', '')} {matched_candidate.get('description', '')}"
            if not self.news_engine.validate_number_guard(summary, cand_text):
                summary = matched_candidate.get("description") or matched_candidate.get("representative_title", headline)

            results.append({
                "slide_index": slide_idx,
                "formatted_index": f"{slide_idx:02d}",
                "headline": headline,
                "badge": badge,
                "summary": summary,
                "photo_scene": photo_scene,
                "raw_prompt": block,
                "handle": "@HEADLIGHTNEWS"
            })

        return results

    def _plan_headlight_heuristically(self, candidates: List[Dict[str, Any]], target_count: int = 9) -> List[Dict[str, Any]]:
        """Deterministic heuristic builder matching the exact @HEADLIGHTNEWS template."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%A, %d %B %Y").upper()
        results = []
        for idx in range(min(target_count, len(candidates))):
            slide_idx = idx + 1
            c = candidates[idx]
            rep_title = c.get("representative_title", f"India Breaking News Headline {slide_idx}").upper()
            desc = c.get("description", rep_title)
            category = c.get("category", "Top News").upper()
            badge = category if len(category.split()) <= 3 else "TOP UPDATE"

            anchor = "dramatic photojournalistic style, low atmospheric lighting, editorial documentary framing, 35mm depth of field"
            scene = f"modern photojournalistic view in India relating to {category.lower()}, realistic subjects and setting, {anchor}"

            block = (
                f"Headline Section:\n"
                f"A professional breaking news vertical infographic. At the top left, neat black uppercase text displaying today's date: \"{date_str}\". At the top right, a black triple chevron icon (>>>).\n\n"
                f"Dynamic Text:\n"
                f'Large, bold black uppercase typography reading: "{rep_title}".\n'
                f'Directly below the headline, a solid bright red horizontal rectangular box containing white bold uppercase text: "{badge}".\n'
                f'Below the red box, smaller black body text with exact spelling: "{desc}".\n\n'
                f"Dynamic Image:\n"
                f"In the center, a soft, smooth white-to-fog fade transitions into the main photograph below. The photograph is a {scene}.\n\n"
                f"Footer Section:\n"
                f'At the bottom left, a clean red square badge with white number "{slide_idx:02d}". At the bottom right, white bold text handle: "@HEADLIGHTNEWS".'
            )

            results.append({
                "slide_index": slide_idx,
                "formatted_index": f"{slide_idx:02d}",
                "headline": rep_title,
                "badge": badge,
                "summary": desc,
                "photo_scene": scene,
                "raw_prompt": block,
                "handle": "@HEADLIGHTNEWS"
            })
        return results

    def plan_headlight_edition(self, candidates: List[Dict[str, Any]], target_count: int = 9) -> List[Dict[str, Any]]:
        """Generates 9 @HEADLIGHTNEWS prompts using Gemini AI, with fallback."""
        parsed = []
        if config.GEMINI_API_KEY:
            prompt = self.build_headlight_prompt(candidates, target_count=target_count)
            raw = self._call_gemini_text(prompt)
            if raw:
                parsed = self.parse_headlight_blocks(raw, candidates, target_count=target_count)

        if len(parsed) < target_count:
            heuristic_items = self._plan_headlight_heuristically(candidates, target_count=target_count)
            for h_item in heuristic_items[len(parsed):target_count]:
                slide_idx = len(parsed) + 1
                h_item["slide_index"] = slide_idx
                h_item["formatted_index"] = f"{slide_idx:02d}"
                h_item["raw_prompt"] = re.sub(r'white number "\d+"', f'white number "{slide_idx:02d}"', h_item["raw_prompt"])
                parsed.append(h_item)

        return parsed


