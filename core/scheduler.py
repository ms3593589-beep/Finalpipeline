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
        Determines whether execution is for slot1 or slot2.
        Survives GitHub Actions cron drift: hour < 8 UTC -> slot1; >= 8 UTC -> slot2.
        """
        forced = forced_slot.lower().strip()
        if forced in ("slot1", "slot2"):
            return forced

        if current_utc_hour is None:
            current_utc_hour = datetime.now(timezone.utc).hour

        return "slot1" if current_utc_hour < 8 else "slot2"

    def determine_mode(
        self,
        slot: str,
        custom_topic: str = "",
        news_story_count: int = 10,
        now: Optional[datetime] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determines operating mode and relevant contextual payload.
        Returns: (mode, context_dict)
        Modes:
          'B': Custom Topic override
          'N': News edition
          'C': Active festival
          'D': Weekday evergreen theme fallback
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Mode B: Explicit topic
        if custom_topic and custom_topic.strip():
            return "B", {"topic": custom_topic.strip()}

        weekday = now.weekday()
        current_theme = self.theme_manager.get_theme_for_weekday(weekday)

        if slot == "slot1":
            # Slot 1: Morning News Edition
            if news_story_count >= config.NEWS_MIN_STORIES:
                return "N", {"edition": "Morning Edition"}
            # Fallback if fewer than 5 news stories
            return "D", {"theme": current_theme, "fallback_reason": "Insufficient news stories"}

        # Slot 2: Evening Slot
        # Check active festival window [T-10 ... T+1]
        active_fest, days_diff = self.festival_engine.get_active_festival(now.date())
        if active_fest:
            return "C", {"festival": active_fest, "days_diff": days_diff}

        # No active festival: check Slot 2 fallback
        if config.SLOT2_FALLBACK == "news" and news_story_count >= config.NEWS_MIN_STORIES:
            return "N", {"edition": "Evening Edition"}

        # Evergreen theme fallback
        return "D", {"theme": current_theme, "fallback_reason": "Slot 2 evergreen schedule"}
