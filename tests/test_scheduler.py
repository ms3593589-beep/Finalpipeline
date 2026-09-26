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

    def test_mode_determination_always_mode_n(self):
        # 1. Standard run returns Mode N
        mode, ctx = self.scheduler.determine_mode(news_story_count=8)
        self.assertEqual(mode, "N")
        self.assertEqual(ctx["edition"], "Daily News Edition")

        # 2. Quiet news day also returns Mode N
        mode_q, ctx_q = self.scheduler.determine_mode(news_story_count=3)
        self.assertEqual(mode_q, "N")
        self.assertEqual(ctx_q["edition"], "Daily News Edition")


if __name__ == "__main__":
    unittest.main()
