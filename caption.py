"""Caption generation, 5-tier hashtag pyramid enforcement, and 2,200 character limits."""

import re
from typing import Dict, Any, List, Optional
from core import config


class CaptionGenerator:
    """Formats Instagram carousel captions and enforces the 5-tier hashtag pyramid."""

    DEFAULT_FALLBACK_TAGS = [
        "indianews", "dailyindia", "currentaffairs", "indiatoday", "topstories",
        "breakingindia", "visualjournalism", "indianculture", "incredibleindia",
        "aestheticindia", "curateddaily", "trendingnow", "newsupdates", "discoverindia",
        "indiaunfold", "editorialvisuals", "insightsofindia", "exploringindia",
        "dailydigest", "stayinformed", "knowledgeispower", "newsfeed", "smartnews",
        "graphicjournalism", "indiansubcontinent", "heritageandfuture", "instanewsindia", "spotlightindia"
    ]

    def __init__(self):
        self.tier_counts = config.HASHTAG_TIER_COUNTS

    @staticmethod
    def clean_hashtag(tag: str) -> str:
        """Normalizes hashtag to lowercase '#[a-z0-9_]+'."""
        clean = tag.strip().lower().lstrip("#")
        clean = re.sub(r"[^a-z0-9_]", "", clean)
        return f"#{clean}" if clean else ""

    def build_hashtag_pyramid(
        self,
        tier_suggestions: Optional[Dict[str, List[str]]] = None,
        backup_pool: Optional[List[str]] = None
    ) -> List[str]:
        """
        Builds exactly 28 (or configured total) hashtags according to the 5 tiers:
        - Niche (default 6)
        - Aesthetic (default 6)
        - Cultural (default 5)
        - Utility (default 6)
        - Discovery (default 5)
        Guarantees deduplication, format validation, shortfall backfilling, and excess truncation.
        """
        if tier_suggestions is None:
            tier_suggestions = {}
        if backup_pool is None:
            backup_pool = self.DEFAULT_FALLBACK_TAGS

        seen_tags = set()
        clean_backup = []
        for tag in backup_pool:
            ct = self.clean_hashtag(tag)
            if ct and ct not in seen_tags:
                clean_backup.append(ct)
                seen_tags.add(ct)

        pyramid_tags = []
        used_global = set()

        backup_idx = 0
        for tier_name, required_count in self.tier_counts.items():
            raw_tags = tier_suggestions.get(tier_name, [])
            tier_selected = []

            for rt in raw_tags:
                ct = self.clean_hashtag(rt)
                if ct and ct not in used_global:
                    tier_selected.append(ct)
                    used_global.add(ct)
                    if len(tier_selected) == required_count:
                        break

            # Shortfall backfill
            while len(tier_selected) < required_count:
                if backup_idx < len(clean_backup):
                    candidate = clean_backup[backup_idx]
                    backup_idx += 1
                    if candidate not in used_global:
                        tier_selected.append(candidate)
                        used_global.add(candidate)
                else:
                    # Synthetic fill
                    fill_tag = f"#india_{tier_name}_{len(tier_selected)+1}"
                    if fill_tag not in used_global:
                        tier_selected.append(fill_tag)
                        used_global.add(fill_tag)

            pyramid_tags.extend(tier_selected)

        return pyramid_tags

    def generate_caption(
        self,
        hook: str,
        micro_story: str,
        poll_cta: str = "Which story impact surprised you most? Drop your vote below! 👇",
        save_reminder: str = "📌 Save this edition for your daily briefing & share with friends!",
        hashtags: Optional[List[str]] = None,
        source_credit: str = "Compiled from leading verified news wires.",
        tier_suggestions: Optional[Dict[str, List[str]]] = None,
        backup_pool: Optional[List[str]] = None
    ) -> str:
        """
        Assembles standard carousel caption with character truncation guard (<= 2,200 chars).
        """
        if hashtags is None:
            hashtags = self.build_hashtag_pyramid(tier_suggestions, backup_pool)

        tags_block = " ".join(hashtags)
        ai_disclosure = "🎨 Imagery: Symbolic editorial AI-generated illustrations."
        channel_callout = f"Follow {config.BRAND_HANDLE} for daily visual briefings."

        def assemble(story_text: str) -> str:
            parts = [
                hook.strip(),
                "",
                story_text.strip(),
                "",
                f"🔗 {source_credit}",
                f"✦ {ai_disclosure}",
                "",
                f"🗣️ {poll_cta}",
                f"{save_reminder}",
                "",
                channel_callout,
                "",
                tags_block
            ]
            return "\n".join(parts).strip()

        caption = assemble(micro_story)

        # Character limit check (Meta Graph API limit is 2,200 chars)
        if len(caption) > config.MAX_CAPTION_CHARS:
            overflow = len(caption) - config.MAX_CAPTION_CHARS
            # Trim micro-story first
            trimmed_story_len = max(0, len(micro_story) - overflow - 10)
            trimmed_story = micro_story[:trimmed_story_len].rsplit(" ", 1)[0] + "..."
            caption = assemble(trimmed_story)

            # If still over due to tags/callouts, truncate total
            if len(caption) > config.MAX_CAPTION_CHARS:
                caption = caption[:config.MAX_CAPTION_CHARS - 3] + "..."

        return caption
