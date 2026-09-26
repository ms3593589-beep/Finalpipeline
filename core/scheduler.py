"""Pipeline scheduler dedicated to Mode N (India's Daily Top News carousel)."""

from typing import Dict, Any, Tuple, Optional


class PipelineScheduler:
    """Routes execution slots and ensures dedicated Mode N (Daily News Edition) operation."""

    @staticmethod
    def resolve_slot(forced_slot: str = "auto", current_utc_hour: Optional[int] = None) -> str:
        """
        Single daily slot operation (Morning 07:00 IST / 01:30 UTC).
        Always resolves to 'slot1'.
        """
        return "slot1"

    def determine_mode(
        self,
        slot: str = "slot1",
        news_story_count: int = 10,
        now: Optional[Any] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Always returns Mode N (Daily News Edition).
        """
        return "N", {"edition": "Daily News Edition"}

