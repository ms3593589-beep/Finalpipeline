"""Festival calendar and active window calculation engine."""

import json
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from core import config


class FestivalEngine:
    """Manages multi-year festival calendar and evaluates active publishing windows."""

    def __init__(self):
        self.festivals = self._load_festivals()

    def _load_festivals(self) -> List[Dict[str, Any]]:
        if config.FESTIVALS_FILE.exists():
            try:
                with open(config.FESTIVALS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_active_festival(
        self,
        target_date: Optional[date] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """
        Checks if target_date falls within the active window [T-10 ... T+1] of any festival.
        Returns: (festival_dict, days_diff_to_event) or (None, None).
        If multiple festivals qualify, selects the one closest to its primary event date.
        """
        if target_date is None:
            target_date = datetime.now().date()

        year_str = str(target_date.year)
        active_candidates = []

        has_year_entries = False
        for fest in self.festivals:
            dates_dict = fest.get("dates", {})
            if year_str in dates_dict:
                has_year_entries = True
                try:
                    event_date = datetime.strptime(dates_dict[year_str], "%Y-%m-%d").date()
                    delta_days = (event_date - target_date).days
                    # Active window: T-10 days before event up to T+1 day after event
                    # i.e., delta_days in range [-1, 10]
                    if -1 <= delta_days <= 10:
                        active_candidates.append((abs(delta_days), delta_days, fest, event_date))
                except ValueError:
                    continue

        if not has_year_entries:
            # Emit operational warning: calendar missing dates for this year
            pass

        if not active_candidates:
            return None, None

        # Sort by smallest absolute distance to peak celebration date
        active_candidates.sort(key=lambda x: x[0])
        best = active_candidates[0]
        festival_copy = dict(best[2])
        festival_copy["event_date"] = best[3].isoformat()
        return festival_copy, best[1]

    def has_year_data(self, year: int) -> bool:
        """Returns True if any festival defines dates for the given year."""
        year_str = str(year)
        return any(year_str in f.get("dates", {}) for f in self.festivals)
