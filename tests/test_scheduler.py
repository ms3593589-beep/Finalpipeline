"""Unit tests for PipelineScheduler: hour-based slot resolution and fallback routing."""

import unittest
from datetime import datetime, timezone
from core.scheduler import PipelineScheduler


class TestPipelineScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = PipelineScheduler()

    def test_single_slot_resolution(self):
        # Always resolves to slot1 across all hours in single-slot mode
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=1), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=8), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=13), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="auto", current_utc_hour=23), "slot1")

        # Forced slot overrides
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="slot1", current_utc_hour=15), "slot1")
        self.assertEqual(self.scheduler.resolve_slot(forced_slot="daily", current_utc_hour=2), "slot1")

    def test_mode_determination_and_fallback(self):
        # 1. Custom topic -> Mode B
        mode_b, ctx_b = self.scheduler.determine_mode(custom_topic="Sacred Rivers")
        self.assertEqual(mode_b, "B")
        self.assertEqual(ctx_b["topic"], "Sacred Rivers")

        # 2. News with >= 5 stories (no active festival on a non-festival date)
        # Using a date far from festivals (e.g. 2026-06-15)
        non_fest_date = datetime(2026, 6, 15, 1, 30, tzinfo=timezone.utc)
        mode_n, ctx_n = self.scheduler.determine_mode(news_story_count=8, now=non_fest_date)
        self.assertEqual(mode_n, "N")

        # 3. News with < 5 stories -> Mode D fallback
        mode_d, ctx_d = self.scheduler.determine_mode(news_story_count=3, now=non_fest_date)
        self.assertEqual(mode_d, "D")
        self.assertIn("theme", ctx_d)


if __name__ == "__main__":
    unittest.main()
