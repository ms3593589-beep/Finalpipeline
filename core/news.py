"""News ingestion, clustering, ranking, filtering, and scoring engine."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from email.utils import parsedate_to_datetime

from core import config
from core.state import StateManager


class NewsEngine:
    """Collects Indian news via RSS, deduplicates, clusters, scores, and filters stories."""

    def __init__(self):
        self.state_mgr = StateManager()

    def fetch_feed(self, feed_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetches and parses RSS/Atom XML feed without crashing on errors."""
        items = []
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(feed_info["url"], headers=headers, timeout=12)
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.content)
            
            # Handle RSS 2.0 (<channel><item>...)
            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                desc = item.findtext("description", "").strip()
                pub_date_str = item.findtext("pubDate", "")
                link = item.findtext("link", "").strip()
                
                # Strip HTML tags from description/title
                title = re.sub(r"<[^>]+>", "", title)
                desc = re.sub(r"<[^>]+>", "", desc)

                pub_time = self._parse_pub_date(pub_date_str)
                if title:
                    items.append({
                        "title": title,
                        "description": desc,
                        "pub_time": pub_time,
                        "link": link,
                        "source": feed_info["name"],
                        "category": feed_info.get("category", "Top")
                    })

            # Handle Atom (<entry>...)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip()
                desc = entry.findtext("atom:summary", "", ns) or entry.findtext("atom:content", "", ns) or ""
                pub_date_str = entry.findtext("atom:published", "", ns) or entry.findtext("atom:updated", "", ns)
                link_elem = entry.find("atom:link", ns)
                link = link_elem.get("href", "") if link_elem is not None else ""

                title = re.sub(r"<[^>]+>", "", title)
                desc = re.sub(r"<[^>]+>", "", desc)

                pub_time = self._parse_pub_date(pub_date_str)
                if title:
                    items.append({
                        "title": title,
                        "description": desc,
                        "pub_time": pub_time,
                        "link": link,
                        "source": feed_info["name"],
                        "category": feed_info.get("category", "Top")
                    })
        except Exception:
            # Failing feed is skipped, not fatal
            return []
        return items

    @staticmethod
    def _parse_pub_date(date_str: str) -> datetime:
        """Robust RFC822 / ISO8601 date parser returning UTC datetime."""
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        try:
            # Try ISO 8601
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def tokenize(text: str) -> Set[str]:
        """Extracts normalized significant tokens for cluster comparison."""
        words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "that", "this", "with", "from", "have", "india",
            "said", "after", "will", "news", "over", "into", "been", "were", "more"
        }
        return {w for w in words if w not in stopwords}

    def compute_similarity(self, title1: str, title2: str) -> float:
        """Computes token Jaccard similarity between two headlines."""
        tokens1 = self.tokenize(title1)
        tokens2 = self.tokenize(title2)
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        return len(intersection) / len(union)

    def is_headline_in_history(self, title: str, history: List[Dict[str, Any]], threshold: float = 0.55) -> bool:
        """Verifies headline does not repeat recently covered stories."""
        for past_item in history:
            past_title = past_item.get("headline", "")
            if self.compute_similarity(title, past_title) >= threshold:
                return True
        return False

    def is_skip_story(self, text: str) -> bool:
        """Checks if text contains blacklisted / harmful keywords."""
        lower = text.lower()
        for kw in config.SKIP_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return True
        return False

    def is_sensitive_story(self, text: str) -> bool:
        """Checks if story involves disaster/tragedy requiring symbolic softening."""
        lower = text.lower()
        for kw in config.SENSITIVE_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return True
        return False

    @staticmethod
    def validate_number_guard(summary: str, source_text: str) -> bool:
        """
        Validates that any numbers appearing in the summary exist in the source text.
        Prevents LLM hallucinations on numeric statistics.
        """
        summary_nums = re.findall(r"\b\d+(?:[\.,]\d+)?\b", summary)
        source_nums = set(re.findall(r"\b\d+(?:[\.,]\d+)?\b", source_text))
        for num in summary_nums:
            # Check normalized number
            clean_num = num.replace(",", "")
            normalized_source = {s.replace(",", "") for s in source_nums}
            if clean_num not in normalized_source:
                return False
        return True

    def collect_and_rank_stories(
        self,
        raw_items: Optional[List[Dict[str, Any]]] = None,
        max_age_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingests, filters, clusters, and ranks news stories.
        Returns top clustered stories ordered by score.
        """
        if max_age_hours is None:
            max_age_hours = config.NEWS_MAX_AGE_HOURS

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_age_hours)

        if raw_items is None:
            raw_items = []
            for feed in config.NEWS_FEEDS:
                raw_items.extend(self.fetch_feed(feed))

        history = self.state_mgr.load_news_history()

        # Step 1: Filter raw items
        valid_items = []
        for it in raw_items:
            # Age filter
            if it.get("pub_time", now) < cutoff:
                continue
            combined_text = f"{it['title']} {it['description']}"
            # Skip offensive / harmful
            if self.is_skip_story(combined_text):
                continue
            # Check history
            if self.is_headline_in_history(it["title"], history):
                continue
            valid_items.append(it)

        # Step 2: Cluster near-duplicate stories
        clusters: List[Dict[str, Any]] = []
        for it in valid_items:
            merged = False
            for c in clusters:
                # Compare with representative title
                if self.compute_similarity(it["title"], c["representative_title"]) >= 0.4:
                    c["items"].append(it)
                    c["sources"].add(it["source"])
                    if it.get("pub_time", now) > c["latest_time"]:
                        c["latest_time"] = it.get("pub_time", now)
                    merged = True
                    break
            if not merged:
                clusters.append({
                    "representative_title": it["title"],
                    "description": it["description"],
                    "category": it["category"],
                    "items": [it],
                    "sources": {it["source"]},
                    "latest_time": it.get("pub_time", now)
                })

        # Step 3: Score clusters
        for c in clusters:
            distinct_outlets = len(c["sources"])
            item_count = len(c["items"])
            # Recency bonus: up to 3 points for stories within last 4 hours
            age_hours = (now - c["latest_time"]).total_seconds() / 3600.0
            recency_bonus = max(0.0, 3.0 - (age_hours / 4.0))
            score = (3.0 * distinct_outlets) + recency_bonus + (0.5 * item_count)
            c["score"] = score
            c["is_sensitive"] = self.is_sensitive_story(f"{c['representative_title']} {c['description']}")

        # Sort clusters by score descending
        clusters.sort(key=lambda x: x["score"], reverse=True)

        # Step 4: Category diversity filter (max 3 stories per category)
        category_counts: Dict[str, int] = {}
        diverse_stories: List[Dict[str, Any]] = []
        for c in clusters:
            cat = c["category"]
            if category_counts.get(cat, 0) < config.NEWS_MAX_PER_CATEGORY:
                category_counts[cat] = category_counts.get(cat, 0) + 1
                diverse_stories.append(c)
            if len(diverse_stories) >= config.NEWS_MAX_STORIES:
                break

        # If diversity filter left fewer stories, backfill from remaining high-scoring clusters
        if len(diverse_stories) < config.NEWS_MAX_STORIES:
            for c in clusters:
                if c not in diverse_stories:
                    diverse_stories.append(c)
                if len(diverse_stories) >= config.NEWS_MAX_STORIES:
                    break

        return diverse_stories
