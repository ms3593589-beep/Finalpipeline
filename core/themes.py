"""Evergreen weekday theme manager."""

import json
from typing import Dict, Any, Optional
from core import config


class ThemeManager:
    """Provides curated Indian heritage themes for each day of the week."""

    def __init__(self):
        self.themes = self._load_themes()

    def _load_themes(self) -> Dict[str, Any]:
        if config.EVERGREEN_THEMES_FILE.exists():
            try:
                with open(config.EVERGREEN_THEMES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Fallback theme if file missing
        return {
            str(i): {
                "day": "Day",
                "theme": "Sacred Indian Heritage",
                "slug": "sacred-heritage",
                "palette": ["#D9531E", "#2A5B84", "#F4C430", "#3E2723", "#F5EBE6"],
                "style_lock": "Classic Indian heritage art, sacred geometry, traditional pigments, warm lighting",
                "narrative_concepts": ["Timeless heritage of ancient India"],
                "prompt_keywords": ["sacred heritage", "indian art"],
                "hashtag_pool": ["indianheritage", "incredibleindia", "ancientindia", "traditionalart"]
            }
            for i in range(7)
        }

    def get_theme_for_weekday(self, weekday: int) -> Dict[str, Any]:
        """Returns the theme specification for 0=Monday .. 6=Sunday."""
        key = str(weekday % 7)
        return self.themes.get(key, self.themes[list(self.themes.keys())[0]])
