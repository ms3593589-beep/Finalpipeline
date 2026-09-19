"""Unit tests for PipelineScheduler: hour-based slot resolution and fallback routing."""

import unittest
from datetime import datetime, timezone
from core.scheduler import PipelineScheduler


class TestPipelineScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = PipelineScheduler()

    def test_slot_selection_by_hour_window(self):
        # Morning hours (< 8 UTC) -> slot1
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=1), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=5), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=7), "slot1")

        # Evening hours (>= 8 UTC) -> slot2
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=8), "slot2")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=13), "slot2")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=23), "slot2")

        # Forced slot overrides
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="slot1", current_utc_hour=15), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="slot2", current_utc_hour=2), "slot2")

    def test_insufficient_news_stories_triggers_mode_d_fallback(self):
        # In slot 1 with only 3 stories (< NEWS_MIN_STORIES = 5)
        mode, context = self.scheduler.determine_mode(slot="slot1", news_story_count=3)
        self.assertEqual(mode, "D")
        self.assertIn("theme", context)

        # In slot 1 with 8 stories (>= 5) -> Mode N
        mode, context = self.scheduler.determine_mode(slot="slot1", news_story_count=8)
        self.assertEqual(mode, "N")


if __name__ == "__main__":
    unittest.main()
