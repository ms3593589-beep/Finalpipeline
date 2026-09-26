"""Pipeline scheduler and operating mode router."""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from core import config
from core.festivals import FestivalEngine
from core.themes import ThemeManager


class PipelineScheduler:
    """Routes execution slots, detects active festivals, and chooses operating modes."""

    def __init__(self):
        self.festival_engine = FestivalEngine()
        self.theme_manager = ThemeManager()

    @staticmethod
    def resolve_slot(forced_slot: str = "auto", current_utc_hour: Optional[int] = None) -> str:
        """
        Single daily slot operation (Slot 1: Morning 07:00 IST / 01:30 UTC).
        Always resolves to 'slot1'.
        """
        forced = forced_slot.lower().strip()
        if forced in ("slot1", "daily"):
            return "slot1"
        return "slot1"

    def determine_mode(
        self,
        slot: str = "slot1",
        custom_topic: str = "",
        news_story_count: int = 10,
        now: Optional[datetime] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determines operating mode and relevant contextual payload for the daily slot:
          'B': Custom Topic override
          'C': Active festival celebration (T-10 ... T+1 window)
          'N': Daily news edition (if usable stories >= NEWS_MIN_STORIES)
          'D': Weekday evergreen theme fallback
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Mode B: Explicit topic override
        if custom_topic and custom_topic.strip():
            return "B", {"topic": custom_topic.strip()}

        weekday = now.weekday()
        current_theme = self.theme_manager.get_theme_for_weekday(weekday)

        # Mode C: Check active festival window [T-10 ... T+1]
        active_fest, days_diff = self.festival_engine.get_active_festival(now.date())
        if active_fest:
            return "C", {"festival": active_fest, "days_diff": days_diff}

        # Mode N: Daily News Edition
        if news_story_count >= config.NEWS_MIN_STORIES:
            return "N", {"edition": "Daily Edition"}

        # Mode D: Fallback to evergreen weekday theme if fewer than 5 news stories
        return "D", {"theme": current_theme, "fallback_reason": "Insufficient news stories"}
